package kr.yoonsu.staralbum;

import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class AlbumResponse {
    private static final Pattern MP4 = Pattern.compile("episodes/([a-z0-9-]+)/film\\.mp4");
    private static final Pattern RANGE = Pattern.compile("bytes=(\\d*)-(\\d*)");

    static WebResourceResponse serve(AlbumCatalog catalog, WebResourceRequest request) {
        if (!AlbumActivity.local(request.getUrl()) || !"GET".equals(request.getMethod())) {
            return empty(403, "Forbidden", new HashMap<>());
        }
        String path = request.getUrl().getEncodedPath();
        if (catalog == null || path == null || path.length() < 2) {
            return empty(404, "Not Found", new HashMap<>());
        }
        String name = path.substring(1);
        Map<String, String> headers = new HashMap<>();
        headers.put("X-Content-Type-Options", "nosniff");
        headers.put("Cache-Control", "no-store");
        byte[] file = catalog.files.get(name);
        if (file != null) {
            String type = name.endsWith(".html") ? "text/html" : name.endsWith(".js")
                    ? "application/javascript" : name.endsWith(".css") ? "text/css" : "image/jpeg";
            if ("text/html".equals(type)) {
                headers.put("Content-Security-Policy", "default-src 'self'; object-src 'none'; "
                        + "style-src 'self'; script-src 'self'; img-src 'self'; media-src 'self'");
            }
            return reply(type, type.startsWith("image/") ? null : "UTF-8", 200, "OK",
                    headers, new ByteArrayInputStream(file));
        }
        Matcher video = MP4.matcher(name);
        if (video.matches()) {
            AlbumCatalog.Video entry = catalog.videos.get(video.group(1));
            if (entry != null) return movie(catalog, entry, header(request, "Range"), headers);
        }
        return empty(404, "Not Found", headers);
    }

    private static String header(WebResourceRequest request, String name) {
        for (Map.Entry<String, String> item : request.getRequestHeaders().entrySet()) {
            if (name.equalsIgnoreCase(item.getKey())) return item.getValue();
        }
        return null;
    }

    private static WebResourceResponse movie(AlbumCatalog catalog, AlbumCatalog.Video video,
            String range, Map<String, String> headers) {
        long start = 0;
        long end = video.size - 1;
        boolean partial = range != null;
        headers.put("Accept-Ranges", "bytes");
        if (partial) {
            Matcher match = RANGE.matcher(range.trim());
            try {
                if (!match.matches()) throw new NumberFormatException();
                String left = match.group(1);
                String right = match.group(2);
                if (left.isEmpty()) start = Math.max(0, video.size - Long.parseLong(right));
                else {
                    start = Long.parseLong(left);
                    if (!right.isEmpty()) end = Math.min(end, Long.parseLong(right));
                }
                if (start > end) throw new NumberFormatException();
            } catch (NumberFormatException error) {
                headers.put("Content-Range", "bytes */" + video.size);
                return empty(416, "Range Not Satisfiable", headers);
            }
            headers.put("Content-Range", "bytes " + start + "-" + end + "/" + video.size);
        }
        long length = end - start + 1;
        headers.put("Content-Length", Long.toString(length));
        return reply("video/mp4", null, partial ? 206 : 200,
                partial ? "Partial Content" : "OK", headers, new MovieStream(catalog, video, start, length));
    }

    private static WebResourceResponse empty(int code, String reason, Map<String, String> headers) {
        return reply("text/plain", "UTF-8", code, reason, headers, new ByteArrayInputStream(new byte[0]));
    }

    private static WebResourceResponse reply(String type, String encoding, int status, String reason,
            Map<String, String> headers, InputStream stream) {
        return new WebResourceResponse(type, encoding, status, reason, headers, stream);
    }

    private static final class MovieStream extends InputStream {
        private final AlbumCatalog catalog;
        private final AlbumCatalog.Video video;
        private long position, remaining;

        MovieStream(AlbumCatalog catalog, AlbumCatalog.Video video, long start, long length) {
            this.catalog = catalog;
            this.video = video;
            this.position = start;
            this.remaining = length;
        }

        @Override public int read() throws IOException {
            if (remaining == 0) return -1;
            byte[] one = new byte[1];
            read(one, 0, 1);
            return one[0] & 255;
        }

        @Override public int read(byte[] out, int offset, int count) throws IOException {
            if (count == 0) return 0;
            if (remaining == 0) return -1;
            int index = (int) (position / AlbumCatalog.CHUNK);
            int from = (int) (position % AlbumCatalog.CHUNK);
            byte[] plain = catalog.block(video, index);
            int length = (int) Math.min(Math.min(count, plain.length - from), remaining);
            System.arraycopy(plain, from, out, offset, length);
            position += length;
            remaining -= length;
            return length;
        }

        @Override public long skip(long n) {
            long amount = Math.max(0, Math.min(n, remaining));
            position += amount;
            remaining -= amount;
            return amount;
        }

        @Override public int available() { return (int) Math.min(remaining, AlbumCatalog.CHUNK); }
    }
}
