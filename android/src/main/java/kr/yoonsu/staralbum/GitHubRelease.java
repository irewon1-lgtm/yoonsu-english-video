package kr.yoonsu.staralbum;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;

final class GitHubRelease {
    static final String ROOT = "https://raw.githubusercontent.com/irewon1-lgtm/yoonsu-english-video/album-media/";
    static final String LATEST = ROOT + "latest.bundle";

    static byte[] catalog(String address, int maxBytes) throws IOException {
        HttpURLConnection connection = open(address, null);
        try {
            if (connection.getResponseCode() != 200) throw new IOException("Album unavailable");
            try (InputStream in = connection.getInputStream()) {
                return readBounded(in, maxBytes);
            }
        } finally {
            connection.disconnect();
        }
    }

    static byte[] range(String address, long start, int length, long total) throws IOException {
        long end = start + length - 1;
        HttpURLConnection connection = open(address, "bytes=" + start + "-" + end);
        try {
            int status = connection.getResponseCode();
            String expected = "bytes " + start + "-" + end + "/" + total;
            if (status != 206 || !expected.equals(connection.getHeaderField("Content-Range"))) {
                throw new IOException("Video range unavailable");
            }
            try (InputStream in = connection.getInputStream()) {
                byte[] payload = readBounded(in, length);
                if (payload.length != length) throw new IOException("Truncated video block");
                return payload;
            }
        } finally {
            connection.disconnect();
        }
    }

    private static HttpURLConnection open(String address, String range) throws IOException {
        URL url = new URL(address);
        for (int hop = 0; hop < 5; hop++) {
            String host = url.getHost();
            if (!"https".equals(url.getProtocol()) || url.getUserInfo() != null
                    || (url.getPort() != -1 && url.getPort() != 443)
                    || (!"raw.githubusercontent.com".equals(host) && !"release-assets.githubusercontent.com".equals(host)
                        && !"objects.githubusercontent.com".equals(host))) {
                throw new IOException("Unexpected album host");
            }
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(15000);
            connection.setRequestProperty("Accept-Encoding", "identity");
            connection.setRequestProperty("User-Agent", "YoonsuStarAlbum/2");
            if (range == null) {
                connection.setRequestProperty("Cache-Control", "no-cache");
            } else {
                connection.setRequestProperty("Range", range);
            }
            int status;
            try {
                status = connection.getResponseCode();
            } catch (IOException error) {
                connection.disconnect();
                throw error;
            }
            if (status < 300 || status >= 400) return connection;
            String location = connection.getHeaderField("Location");
            connection.disconnect();
            if (location == null) throw new IOException("Missing album redirect");
            url = new URL(url, location);
        }
        throw new IOException("Too many album redirects");
    }

    static byte[] readBounded(InputStream in, int limit) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        byte[] buffer = new byte[16384];
        int size = 0;
        for (int n; (n = in.read(buffer)) != -1; ) {
            size += n;
            if (size > limit) throw new IOException("Album payload too large");
            out.write(buffer, 0, n);
        }
        return out.toByteArray();
    }
}
