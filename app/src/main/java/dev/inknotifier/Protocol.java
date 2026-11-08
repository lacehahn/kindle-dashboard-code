package dev.inknotifier;

import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

public final class Protocol {
    public static final long TTL = 7L * 24 * 60 * 60 * 1000;
    public static String clip(String s, int bytes) {
        if (s == null || bytes < 3) return "";
        if (s.getBytes(StandardCharsets.UTF_8).length <= bytes) return s;
        StringBuilder b = new StringBuilder(); int used = 0;
        for (int i = 0; i < s.length();) {
            int cp = s.codePointAt(i); String part = new String(Character.toChars(cp));
            int n = part.getBytes(StandardCharsets.UTF_8).length;
            if (used + n > bytes - 3) break;
            b.append(part); used += n; i += Character.charCount(cp);
        }
        return b.append("…").toString();
    }
    public static JSONObject message(String app, String pkg, String title, String body, String instance, long version, long posted) throws Exception {
        JSONObject event = new JSONObject().put("v", 1).put("type", "message").put("id", UUID.randomUUID().toString())
            .put("instance", instance).put("version", version).put("time", posted).put("expires", System.currentTimeMillis() + TTL)
            .put("app", clip(app, 80)).put("pkg", clip(pkg, 180)).put("title", clip(title, 240)).put("body", clip(body, 1500));
        // JSON escaping can double the size of ASCII quotes/backslashes. Reserve room for base64 and GCM.
        int budget = 1500;
        while (event.toString().getBytes(StandardCharsets.UTF_8).length > 2900 && budget > 0) {
            budget = Math.max(0, budget - 100); event.put("body", clip(body, budget));
        }
        return event;
    }
    public static JSONObject ack(String id) throws Exception {
        return new JSONObject().put("v", 1).put("type", "ack").put("id", id).put("expires", System.currentTimeMillis() + TTL);
    }
    public static void validate(JSONObject o, String expected) throws Exception {
        if (o.getInt("v") != 1 || !expected.equals(o.getString("type"))) throw new IllegalArgumentException("Wrong event type");
        UUID.fromString(o.getString("id"));
        long expiry = o.getLong("expires"), now = System.currentTimeMillis();
        if (expiry < now || expiry > now + TTL + 60 * 60 * 1000) throw new IllegalArgumentException("Expired event");
        if (expected.equals("message")) {
            UUID.fromString(o.getString("instance"));
            if (o.getLong("version") < 1 || o.getLong("time") < 0) throw new IllegalArgumentException("Invalid metadata");
            for (String k : new String[]{"app", "pkg", "title", "body"}) if (o.getString(k).length() > 3000) throw new IllegalArgumentException("Oversize event");
        }
    }
}
