package kr.yoonsu.staralbum;

import java.io.File;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Arrays;

public class RuntimeProbe {
    private static void check(boolean pass, String step) {
        if (!pass) throw new AssertionError(step);
    }

    private static short[] signal(int frame, int kind) {
        short[] samples = new short[PhonicsGate.FRAME];
        for (int i = 0; i < samples.length; i++) {
            double t = frame * samples.length + i;
            if (kind == 1) {
                samples[i] = (short) Math.round(2600 * Math.sin(2 * Math.PI * 443 * t / 16000));
            } else if (kind > 1) {
                double x = Math.sin(.091 * t) + .52 * Math.sin(.257 * t) + .38 * Math.sin(.385 * t);
                samples[i] = (short) Math.round((kind == 2 ? 257 : 690) * x);
            }
        }
        return samples;
    }

    public static void main(String[] args) throws Exception {
        PhonicsGate gate = new PhonicsGate(8);
        for (int i = 0; i < 30; i++) {
            check(gate.feed(signal(i, 0)) == PhonicsGate.WAIT, "silence");
            check(gate.feed(signal(i, 1)) == PhonicsGate.WAIT, "single tone");
            check(gate.feed(signal(i, 2)) == PhonicsGate.WAIT, "below RMS 350");
        }
        for (int i = 0; i < 9; i++) {
            check(gate.feed(signal(i, 1)) == PhonicsGate.WAIT, "continuous pure tone");
        }
        check(gate.feed(signal(0, 0)) == PhonicsGate.WAIT, "flush");
        check(gate.feed(signal(0, 3)) == PhonicsGate.WAIT, "20ms");
        check(gate.feed(signal(1, 3)) == PhonicsGate.WAIT, "40ms");
        check(gate.feed(signal(2, 3)) == PhonicsGate.ONSET, "60ms");
        for (int i = 0; i < 14; i++) check(gate.feed(signal(i, 0)) == PhonicsGate.WAIT, "early end");
        check(gate.feed(signal(14, 0)) == PhonicsGate.END, "300 ms");
        System.out.println("PASS AudioRecord PCM gate profile");
        if (args.length == 0) return;

        byte[] key = AlbumCatalog.hex(new String(Files.readAllBytes(new File(args[0]).toPath()),
                StandardCharsets.US_ASCII).trim());
        byte[] old = Files.readAllBytes(new File(args[1]).toPath());
        byte[] hosted = GitHubRelease.catalog(GitHubRelease.LATEST + "?verify=" + System.currentTimeMillis(),
                AlbumCatalog.MAX_BUNDLE);
        AlbumCatalog initial = AlbumCatalog.load(old, key);
        AlbumCatalog fresh = AlbumCatalog.load(hosted, key);
        check(initial.version == 1 && fresh.version == 2, "remote content version update");
        check(fresh.videos.size() == 3 && fresh.files.containsKey("album.js"), "latest catalog files");
        System.out.println("PASS Hosted authenticated update 1 → 2");

        for (AlbumCatalog.Video video : fresh.videos.values()) {
            int last = (int) ((video.size - 1) / AlbumCatalog.CHUNK);
            File source = new File(args[2], video.slug + "/film.mp4");
            try (RandomAccessFile plain = new RandomAccessFile(source, "r")) {
                for (int index : new int[]{0, 1, last / 2, last}) {
                    byte[] actual = fresh.block(video,index);
                    byte[] expected = new byte[actual.length];
                    plain.seek((long) index * AlbumCatalog.CHUNK);
                    plain.readFully(expected);
                    check(Arrays.equals(actual, expected), "original video bytes: "+video.slug);
                }
            }
            System.out.println("PASS 4 hosted byte ranges match 1080p master: " + video.slug);
        }

        hosted[25] ^= 1;
        try {
            AlbumCatalog.load(hosted, key);
            throw new AssertionError("Modified content was accepted");
        } catch (javax.crypto.AEADBadTagException expected) {
            System.out.println("PASS Modified remote bundle rejected");
        }
    }
}
