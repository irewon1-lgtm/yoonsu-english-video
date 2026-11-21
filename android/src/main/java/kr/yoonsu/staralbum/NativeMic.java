package kr.yoonsu.staralbum;

import android.media.AudioFormat;
import android.media.AudioRecord;
import android.media.MediaRecorder;
import android.webkit.JavascriptInterface;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

final class NativeMic {
    private final AlbumActivity activity;
    private final ExecutorService reader = Executors.newSingleThreadExecutor();
    private final AtomicInteger generation = new AtomicInteger();
    private final Object lock = new Object();
    private AudioRecord active;

    NativeMic(AlbumActivity activity) { this.activity = activity; }

    @JavascriptInterface public void authorize() {
        activity.runOnUiThread(new Runnable() {
            @Override public void run() { activity.authorizeMicrophone(); }
        });
    }

    @JavascriptInterface public void listen(final int level, final int token) {
        activity.runOnUiThread(new Runnable() {
            @Override public void run() {
                if (!activity.canCapture() || level < 1 || level > 10) {
                    activity.micEvent("capture-error", token);
                    return;
                }
                stop();
                final int expected = generation.get();
                reader.execute(new Runnable() {
                    @Override public void run() { capture(level, token, expected); }
                });
            }
        });
    }

    @JavascriptInterface public void stop() {
        generation.incrementAndGet();
        synchronized (lock) {
            if (active != null && active.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                try { active.stop(); }
                catch (IllegalStateException ignored) {}
            }
        }
    }

    void close() {
        stop();
        reader.shutdownNow();
    }

    private AudioRecord create(int source) {
        int channels = AudioFormat.CHANNEL_IN_MONO;
        int format = AudioFormat.ENCODING_PCM_16BIT;
        int needed = AudioRecord.getMinBufferSize(PhonicsGate.RATE, channels, format);
        if (needed <= 0) throw new IllegalStateException("Unavailable 16 kHz capture");
        AudioRecord recorder = new AudioRecord(source, PhonicsGate.RATE, channels, format,
                Math.max(needed, 6400));
        if (recorder.getState() != AudioRecord.STATE_INITIALIZED) {
            recorder.release();
            throw new IllegalStateException("Unavailable microphone");
        }
        return recorder;
    }

    private void capture(int level, int token, int expected) {
        AudioRecord recorder = null;
        try {
            try { recorder = create(MediaRecorder.AudioSource.VOICE_RECOGNITION); }
            catch (IllegalStateException error) { recorder = create(MediaRecorder.AudioSource.MIC); }
            synchronized (lock) {
                if (expected != generation.get()) return;
                recorder.startRecording();
                if (recorder.getRecordingState() != AudioRecord.RECORDSTATE_RECORDING) {
                    throw new IllegalStateException("Capture failed");
                }
                active = recorder;
            }
            PhonicsGate gate = new PhonicsGate(level);
            short[] frame = new short[PhonicsGate.FRAME];
            int fill = 0;
            while (expected == generation.get()) {
                int captured = recorder.read(frame, fill, frame.length - fill);
                if (captured < 0) throw new IllegalStateException("Microphone disconnected");
                fill += captured;
                if (fill < frame.length) continue;
                fill = 0;
                int state = gate.feed(frame);
                if (state == PhonicsGate.ONSET) report("onset", token, expected);
                if (state == PhonicsGate.END) {
                    report("end", token, expected);
                    break;
                }
            }
        } catch (RuntimeException error) {
            report("capture-error", token, expected);
        } finally {
            synchronized (lock) {
                if (active == recorder) active = null;
                if (recorder != null) {
                    if (recorder.getRecordingState() == AudioRecord.RECORDSTATE_RECORDING) {
                        try { recorder.stop(); }
                        catch (IllegalStateException ignored) {}
                    }
                    recorder.release();
                }
            }
        }
    }

    private void report(final String type, final int token, final int expected) {
        activity.runOnUiThread(new Runnable() {
            @Override public void run() {
                if (expected == generation.get() && activity.canCapture()) {
                    activity.micEvent(type, token);
                }
            }
        });
    }
}
