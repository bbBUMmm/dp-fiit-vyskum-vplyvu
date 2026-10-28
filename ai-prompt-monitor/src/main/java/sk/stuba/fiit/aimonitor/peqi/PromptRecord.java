package sk.stuba.fiit.aimonitor.peqi;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.Instant;
import java.util.Map;

/**
 * One line of the JSON Lines file written by the mitmproxy capture layer.
 *
 * <p>The capture layer and this class are the two sides of the file interface described
 * in Chapter 7 of the thesis. Unknown properties are ignored on purpose: the capture
 * layer is expected to gain fields as providers change, and a field it adds must never
 * stop the analysis layer from running mid-study.
 *
 * <p>There is no pupil name, no IP address, no cookie and no authorisation header here,
 * and there is no field where one could be put. {@code pseudonym} is
 * {@code sha256(salt | studentCode)} truncated to 16 hex characters, where the salt is
 * held by the school; the researcher cannot reverse it.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
@JsonInclude(JsonInclude.Include.NON_NULL)
public record PromptRecord(
        Instant timestamp,
        String captureId,
        String kind,
        String session,
        String pseudonym,
        String condition,
        Integer period,
        String host,
        String url,
        String method,
        String promptText,
        Integer promptChars,
        Boolean truncated,
        Map<String, Integer> scrubbed
) {

    public static final String KIND_PROMPT = "prompt";
    public static final String KIND_RESPONSE_DIGEST = "response_digest";

    public boolean isPrompt() {
        return KIND_PROMPT.equals(kind);
    }

    /** Number of personal-data items removed before this record was written. */
    public int scrubbedCount() {
        return scrubbed == null ? 0 : scrubbed.values().stream().mapToInt(Integer::intValue).sum();
    }
}
