#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${ANDROID_JAR:?Android API 35 android.jar path required}"
: "${BUILD_TOOLS:?Android 35 build-tools path required}"
: "${ALBUM_KEY_FILE:?Owner content key file required}"
: "${ALBUM_BUNDLE:?Authenticated catalog file required}"
: "${SIGNING_STORE:?Existing Android signing store required}"
: "${SIGNING_PASSWORD_FILE:?Owner signing password file required}"

main=android/src/main
out="$PWD/build"
umask 077
mkdir -p "$out/classes" "$out/dex" "$out/assets"
python3 - "$ALBUM_KEY_FILE" "$out/assets/content.key" <<'PY'
import sys
from pathlib import Path
key = Path(sys.argv[1]).read_bytes()
if len(key) != 32:
    key = bytes.fromhex(key.decode().strip())
if len(key) != 32:
    raise ValueError("Invalid content key")
Path(sys.argv[2]).write_bytes(key)
PY
cp -- "$ALBUM_BUNDLE" "$out/assets/initial.bundle"
"$BUILD_TOOLS/aapt2" compile --dir "$main/res" -o "$out/resources.zip"
"$BUILD_TOOLS/aapt2" link -o "$out/resources.apk" -I "$ANDROID_JAR" \
    --manifest "$main/AndroidManifest.xml" -A "$out/assets" "$out/resources.zip"
sources=("$main/java/kr/yoonsu/staralbum/"*.java)
if [ -n "${ECJ_JAR:-}" ]; then
    java -jar "$ECJ_JAR" -8 -proc:none -bootclasspath "$ANDROID_JAR" -d "$out/classes" "${sources[@]}"
else
    javac --release 8 -cp "$ANDROID_JAR" -d "$out/classes" "${sources[@]}"
fi
mapfile -t classes < <(find "$out/classes" -type f -name '*.class')
"$BUILD_TOOLS/d8" --release --min-api 24 --lib "$ANDROID_JAR" --output "$out/dex" "${classes[@]}"
cp "$out/resources.apk" "$out/unsigned.apk"
(cd "$out/dex" && zip -q -u "$out/unsigned.apk" classes.dex)
"$BUILD_TOOLS/zipalign" -f 4 "$out/unsigned.apk" "$out/aligned.apk"
output="$out/Yoonsu_Star_Album_v2.apk"
"$BUILD_TOOLS/apksigner" sign --ks "$SIGNING_STORE" --ks-key-alias "${SIGNING_ALIAS:-star-album}" \
    --ks-pass "file:$SIGNING_PASSWORD_FILE" --out "$output" "$out/aligned.apk"
"$BUILD_TOOLS/apksigner" verify --verbose --print-certs "$output"
"$BUILD_TOOLS/aapt2" dump badging "$output"
