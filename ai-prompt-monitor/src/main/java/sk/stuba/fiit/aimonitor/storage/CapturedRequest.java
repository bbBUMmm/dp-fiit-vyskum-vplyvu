package sk.stuba.fiit.aimonitor.storage;

import com.fasterxml.jackson.annotation.JsonInclude;

import java.time.Instant;

/**
 * A single captured HTTP(S) request. Persisted as one JSON object per line in the JSONL store.
 *
 * <p>NOTE on privacy: {@code captureId} is a random UUID per request, not a device or user
 * identifier. For the school deployment, generate a per-device opaque hash externally and add it
 * via a {@code deviceHash} field — but never persist raw user identifiers, IPs, or session cookies
 * here. The {@code body} itself may still contain user-identifying content (names, school work);
 * that's exactly the research data, but handle it under the consent + ethics framework described
 * in the README.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record CapturedRequest(
        Instant timestamp,
        String host,
        String url,
        String method,
        String contentType,
        String body,
        String captureId
) {}
