package sk.stuba.fiit.aimonitor.proxy;

import io.netty.buffer.ByteBuf;
import io.netty.channel.ChannelHandlerContext;
import io.netty.handler.codec.http.FullHttpRequest;
import io.netty.handler.codec.http.HttpObject;
import io.netty.handler.codec.http.HttpRequest;
import io.netty.handler.codec.http.HttpResponse;
import org.littleshoot.proxy.HttpFilters;
import org.littleshoot.proxy.HttpFiltersAdapter;
import org.littleshoot.proxy.HttpFiltersSourceAdapter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import sk.stuba.fiit.aimonitor.config.Config;
import sk.stuba.fiit.aimonitor.storage.CapturedRequest;
import sk.stuba.fiit.aimonitor.storage.JsonlStore;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * LittleProxy filter source that inspects every request flowing through the proxy and persists
 * those matching configured URL patterns.
 *
 * <p>For HTTPS, this only works because the proxy is configured with a {@code MitmManager} that
 * terminates TLS using a CA the browser trusts. After TLS decryption the request looks like a
 * normal HTTP request and we can read the body.
 *
 * <p>Matching is a plain substring check against {@code host + uri}, e.g.
 * {@code chatgpt.com/backend-api/conversation}. We deliberately do <em>not</em> do regex here —
 * substring matching is predictable, debuggable and good enough for the walking skeleton.
 */
public class CapturingFiltersSource extends HttpFiltersSourceAdapter {
    private static final Logger log = LoggerFactory.getLogger(CapturingFiltersSource.class);

    private final Config config;
    private final JsonlStore store;

    public CapturingFiltersSource(Config config, JsonlStore store) {
        this.config = config;
        this.store = store;
    }

    /**
     * Returning a positive value here tells LittleProxy to aggregate all incoming request chunks
     * into a single {@link FullHttpRequest} before invoking the filter. Without this we'd receive
     * {@code HttpContent} chunks one at a time and would have to assemble them manually.
     *
     * <p>This limit applies <em>per connection</em>. Requests with bodies larger than this are
     * still proxied — they just aren't aggregated, so we won't be able to capture them.
     */
    @Override
    public int getMaximumRequestBufferSizeInBytes() {
        return config.maxBodySizeKb() * 1024;
    }

    @Override
    public HttpFilters filterRequest(HttpRequest originalRequest, ChannelHandlerContext ctx) {
        return new HttpFiltersAdapter(originalRequest) {
            @Override
            public HttpResponse clientToProxyRequest(HttpObject httpObject) {
                // Because getMaximumRequestBufferSizeInBytes() > 0, the proxy will deliver the
                // request as a single FullHttpRequest once the body has been fully received.
                if (httpObject instanceof FullHttpRequest fullReq) {
                    try {
                        captureIfMatches(fullReq);
                    } catch (Exception e) {
                        log.warn("Error while capturing request", e);
                    }
                }
                // Returning null lets the request continue upstream unchanged. We are observers,
                // not interceptors — the user's request must reach the AI service intact.
                return null;
            }
        };
    }

    private void captureIfMatches(FullHttpRequest req) {
        String host = req.headers().get("Host");
        if (host == null || host.isBlank()) {
            return;
        }

        // For HTTPS requests routed via the MITM, req.uri() is a path like "/api/foo".
        // For plain HTTP via the proxy it may be an absolute URI. Normalize.
        String uri = req.getUri();
        String hostAndPath = uri.startsWith("http://") || uri.startsWith("https://")
                ? uri
                : host + uri;

        if (!matchesAny(hostAndPath, config.urlPatterns())) {
            return;
        }

        String contentType = req.headers().get("Content-Type");
        String body = null;
        ByteBuf content = req.content();
        if (content != null && content.isReadable()) {
            // toString(charset) does NOT consume the buffer — safe to call even though the
            // request continues upstream.
            body = content.toString(StandardCharsets.UTF_8);
        }

        String url = hostAndPath.startsWith("http") ? hostAndPath : "https://" + hostAndPath;

        CapturedRequest captured = new CapturedRequest(
                Instant.now(),
                host,
                url,
                req.getMethod().name(),
                contentType,
                body,
                UUID.randomUUID().toString()
        );

        store.write(captured);
        log.info("Captured {} {} ({} bytes body)",
                captured.method(),
                captured.url(),
                body == null ? 0 : body.length());
    }

    private static boolean matchesAny(String haystack, List<String> patterns) {
        for (String pattern : patterns) {
            if (haystack.contains(pattern)) return true;
        }
        return false;
    }
}
