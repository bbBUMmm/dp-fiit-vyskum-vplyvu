package sk.stuba.fiit.aimonitor.proxy;

import org.littleshoot.proxy.HttpProxyServer;
import org.littleshoot.proxy.impl.DefaultHttpProxyServer;
import org.littleshoot.proxy.mitm.CertificateSniffingMitmManager;
import org.littleshoot.proxy.mitm.RootCertificateException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import sk.stuba.fiit.aimonitor.config.Config;
import sk.stuba.fiit.aimonitor.storage.JsonlStore;

import java.net.InetSocketAddress;

/**
 * Boots LittleProxy with {@link CertificateSniffingMitmManager} from the LittleProxy-mitm
 * extension, which generates per-host leaf certificates signed by a stable root CA. This is
 * what HSTS browsers (Firefox, Chrome) require — they reject CA certs being used directly as
 * server certs.
 *
 * <p>On first run the extension creates {@code littleproxy-mitm.pem} (the public CA cert to
 * import into the browser) and {@code littleproxy-mitm.p12} (the private keystore — never share)
 * in the working directory.
 */
public final class ProxyRunner {
    private static final Logger log = LoggerFactory.getLogger(ProxyRunner.class);

    private ProxyRunner() {}

    public static HttpProxyServer start(Config config, JsonlStore store)
            throws RootCertificateException {

        CertificateSniffingMitmManager mitm = new CertificateSniffingMitmManager();

        HttpProxyServer server = DefaultHttpProxyServer.bootstrap()
                .withAddress(new InetSocketAddress(config.proxyBind(), config.proxyPort()))
                .withManInTheMiddle(mitm)
                .withFiltersSource(new CapturingFiltersSource(config, store))
                .withAllowLocalOnly(true)
                .withName("AiPromptMonitor")
                .start();

        log.info("Proxy listening on {}:{}", config.proxyBind(), config.proxyPort());
        log.info("Configured URL patterns:");
        config.urlPatterns().forEach(p -> log.info("  - {}", p));
        return server;
    }
}