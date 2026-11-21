package kr.yoonsu.staralbum;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

final class AlbumCatalog {
    static final int CHUNK = 1024 * 1024;
    static final int MAX_BUNDLE = 4 * 1024 * 1024;
    static final int TAG_BYTES = 16;
    private static final byte[] AAD = "yoonsu-album-catalog-v1".getBytes(StandardCharsets.US_ASCII);
    private final SecretKeySpec key;
    final int version;
    final Map<String, byte[]> files;
    final Map<String, Video> videos;
    private final Map<String, byte[]> blocks = new LinkedHashMap<String, byte[]>(9, .75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<String, byte[]> unused) {
            return size() > 8;
        }
    };

    private AlbumCatalog(SecretKeySpec key, int version, Map<String, byte[]> files,
            Map<String, Video> videos) {
        this.key = key;
        this.version = version;
        this.files = files;
        this.videos = videos;
    }

    static AlbumCatalog load(byte[] sealed, byte[] rawKey)
            throws IOException, GeneralSecurityException, JSONException {
        if (sealed.length < 28 || sealed.length > MAX_BUNDLE) throw new IOException("Invalid album");
        SecretKeySpec key = new SecretKeySpec(rawKey, "AES");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, sealed, 0, 12));
        cipher.updateAAD(AAD);
        byte[] data = cipher.doFinal(sealed, 12, sealed.length - 12);
        Map<String, byte[]> files = new HashMap<>();
        int unpacked = 0;
        try (ZipInputStream archive = new ZipInputStream(new ByteArrayInputStream(data))) {
            for (ZipEntry entry; (entry = archive.getNextEntry()) != null; ) {
                String name = entry.getName();
                if (entry.isDirectory() || !name.matches("(?:[a-z0-9-]+/)*[a-z0-9-]+\\.(html|js|css|jpg|json)")
                        || files.containsKey(name) || files.size() >= 512) {
                    throw new IOException("Invalid album entry");
                }
                byte[] value = GitHubRelease.readBounded(archive, MAX_BUNDLE - unpacked);
                files.put(name, value);
                unpacked += value.length;
            }
        }
        byte[] meta = files.remove("catalog.json");
        if (meta == null || !files.containsKey("index.html")) throw new IOException("Missing album home");
        JSONObject manifest = new JSONObject(new String(meta, StandardCharsets.UTF_8));
        int version = manifest.getInt("version");
        if (manifest.getInt("schema") != 1 || manifest.getInt("chunk") != CHUNK || version <= 0) {
            throw new IOException("Unsupported album version");
        }
        Map<String, Video> videos = new HashMap<>();
        JSONArray entries = manifest.getJSONArray("videos");
        for (int i = 0; i < entries.length(); i++) {
            JSONObject entry = entries.getJSONObject(i);
            Video video = new Video(entry);
            if (videos.put(video.slug, video) != null
                    || !files.containsKey("episodes/" + video.slug + "/index.html")) {
                throw new IOException("Invalid video entry");
            }
        }
        return new AlbumCatalog(key, version, files, videos);
    }

    synchronized byte[] block(Video video, int index) throws IOException {
        String id = video.slug + ":" + index;
        byte[] found = blocks.get(id);
        if (found != null) return found;
        int plainLength = (int) Math.min(CHUNK, video.size - (long) index * CHUNK);
        if (index < 0 || plainLength <= 0) throw new IOException("Invalid video offset");
        long offset = (long) index * (CHUNK + TAG_BYTES);
        long total = video.size + ((video.size + CHUNK - 1) / CHUNK) * TAG_BYTES;
        byte[] sealed = GitHubRelease.range(video.url, offset, plainLength + TAG_BYTES, total);
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            byte[] iv = ByteBuffer.allocate(12).put(video.nonce).putInt(index).array();
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, iv));
            String aad = "yoonsu-video-v1\n" + video.tag + "\n" + video.slug + "\n" + video.size + "\n" + index;
            cipher.updateAAD(aad.getBytes(StandardCharsets.US_ASCII));
            byte[] value = cipher.doFinal(sealed);
            blocks.put(id, value);
            return value;
        } catch (GeneralSecurityException error) {
            throw new IOException("Video authentication failed", error);
        }
    }

    static byte[] hex(String text) throws IOException {
        if (text.length() % 2 != 0) throw new IOException("Invalid hex");
        byte[] out = new byte[text.length() / 2];
        for (int i = 0; i < out.length; i++) {
            int high = Character.digit(text.charAt(i * 2), 16);
            int low = Character.digit(text.charAt(i * 2 + 1), 16);
            if (high < 0 || low < 0) throw new IOException("Invalid hex");
            out[i] = (byte) ((high << 4) | low);
        }
        return out;
    }

    static final class Video {
        final String tag, slug, url;
        final byte[] nonce;
        final long size;

        Video(JSONObject data) throws JSONException, IOException {
            tag = data.getString("tag");
            slug = data.getString("slug");
            size = data.getLong("bytes");
            nonce = hex(data.getString("nonce"));
            String asset = data.getString("asset");
            if (!tag.matches("album-v[1-9][0-9]{0,8}") || !slug.matches("[a-z0-9]+(?:-[a-z0-9]+)*")
                    || !asset.equals(slug + ".yvideo") || size < 1 || size > 2_000_000_000L
                    || nonce.length != 8) {
                throw new IOException("Invalid video details");
            }
            url = GitHubRelease.ROOT + tag + "/" + asset;
        }
    }
}
