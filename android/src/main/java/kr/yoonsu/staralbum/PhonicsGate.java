package kr.yoonsu.staralbum;

/** Raw PCM gate from the Alpha Phonics 16 kHz sensitivity profile. */
final class PhonicsGate {
    static final int RATE = 16000;
    static final int FRAME = 320;
    private static final int END_SILENCE = 4800;
    private static final int[] THRESHOLDS = {4000,2600,1600,1200,900,700,500,350,160,70};
    static final int WAIT = 0, ONSET = 1, END = 2;

    private final int threshold;
    private final short[] candidate = new short[3 * FRAME];
    private int count, quiet;
    private boolean speaking;

    PhonicsGate(int level) {
        if (level < 1 || level > THRESHOLDS.length) throw new IllegalArgumentException("Sensitivity");
        threshold = THRESHOLDS[level - 1];
    }

    int feed(short[] frame) {
        double energy = 0;
        for (short sample : frame) energy += (double) sample * sample;
        double rms = Math.sqrt(energy / FRAME);
        if (!speaking) {
            if (rms < threshold) {
                count = 0;
                return WAIT;
            }
            System.arraycopy(frame, 0, candidate, count, FRAME);
            count += FRAME;
            if (count < candidate.length) return WAIT;
            count = 0;
            if (singleTone(candidate)) return WAIT;
            speaking = true;
            return ONSET;
        }
        quiet = rms >= threshold * .6 ? 0 : quiet + FRAME;
        return quiet >= END_SILENCE ? END : WAIT;
    }

    private static boolean singleTone(short[] samples) {
        int n = samples.length;
        double mean = 0.0;
        for (short sample : samples) mean += sample;
        mean /= n;
        double[] centered = new double[n];
        double energy = 0.0;
        for (int i = 0; i < n; i++) {
            double x = samples[i] - mean;
            centered[i] = x;
            energy += x * x;
        }
        if (energy <= 0) return true;

        int peak = 1;
        double best = 0.0;
        for (int k = 1; k <= n / 2; k++) {
            double coefficient = 2 * Math.cos(2 * Math.PI * k / n);
            double previous = 0.0, second = 0.0;
            for (double x : centered) {
                double value = x + coefficient * previous - second;
                second = previous;
                previous = value;
            }
            double power = previous * previous + second * second - coefficient * previous * second;
            if (power > best) { best = power; peak = k; }
        }
        for (int offset = -8; offset <= 8; offset++) {
            double bin = peak + offset / 8.0;
            if (bin <= 0 || bin > n / 2) continue;
            double step = 2 * Math.PI * bin / n;
            double cc = 0, ss = 0, cs = 0, cSum = 0, sSum = 0, xc = 0, xs = 0;
            for (int i = 0; i < n; i++) {
                double c = Math.cos(step * i), s = Math.sin(step * i);
                cc += c * c;
                ss += s * s;
                cs += c * s;
                cSum += c;
                sSum += s;
                xc += centered[i] * c;
                xs += centered[i] * s;
            }
            cc -= cSum * cSum / n;
            ss -= sSum * sSum / n;
            cs -= cSum * sSum / n;
            double determinant = cc * ss - cs * cs;
            double explained = determinant > 1e-6
                    ? (ss * xc * xc - 2 * cs * xc * xs + cc * xs * xs) / determinant
                    : xc * xc / cc;
            if (explained / energy >= .985) return true;
        }
        return false;
    }
}
