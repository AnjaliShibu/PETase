#!/usr/bin/env bash
# Local APK build. Needs: JDK 17, Android SDK (ANDROID_HOME) with platform 34 + build-tools.
# Output: dist/petase-ai.apk and dist/petase-ai.apk.idsig
set -euo pipefail
cd "$(dirname "$0")"
: "${ANDROID_HOME:?Set ANDROID_HOME to your Android SDK folder}"
cp index.html android-app/app/src/main/assets/index.html
( cd android-app && chmod +x gradlew && ./gradlew assembleDebug )
BT=$(ls -d "$ANDROID_HOME"/build-tools/* | sort -V | tail -1)
mkdir -p dist
[ -f dist/ks.jks ] || keytool -genkeypair -keystore dist/ks.jks -storepass petase123 -keypass petase123 \
  -alias petase -keyalg RSA -keysize 2048 -validity 3650 -dname "CN=PETase AI Hackathon"
"$BT/zipalign" -f -p 4 android-app/app/build/outputs/apk/debug/app-debug.apk dist/aligned.apk
"$BT/apksigner" sign --ks dist/ks.jks --ks-pass pass:petase123 --key-pass pass:petase123 \
  --ks-key-alias petase --v4-signing-enabled true --out dist/petase-ai.apk dist/aligned.apk
rm dist/aligned.apk
echo "Done -> dist/petase-ai.apk and dist/petase-ai.apk.idsig"
