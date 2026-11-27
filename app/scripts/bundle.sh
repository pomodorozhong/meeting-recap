#!/bin/bash
# Builds MeetingRecap and wraps it in app/.build/MeetingRecap.app. macOS only grants Microphone and Screen & System
# Audio Recording to a real bundle with an Info.plist, not to a bare executable.
#
#   app/scripts/bundle.sh          # build and bundle
#   app/scripts/bundle.sh --test   # also run the tests
#
# The app is signed ad hoc, so each changed build has a new signature and the permissions macOS granted to the old one
# stop working, even though System Settings still shows them as allowed. When the signature changes, this script
# clears both permissions so the next Record asks again (see README.md, "If Record says permission is off"). It
# leaves them alone while the app is running, so a rebuild never cuts off a recording in progress.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--test" ]]; then
    # Command Line Tools keep Swift Testing outside SwiftPM's default search path; Xcode does not need these flags.
    tools=/Library/Developer/CommandLineTools/Library/Developer
    flags=()
    if [[ -d "$tools/Frameworks/Testing.framework" ]]; then
        flags=(-Xswiftc -F -Xswiftc "$tools/Frameworks" -Xlinker -F -Xlinker "$tools/Frameworks"
               -Xlinker -rpath -Xlinker "$tools/Frameworks" -Xlinker -rpath -Xlinker "$tools/usr/lib")
    fi
    swift test ${flags[@]+"${flags[@]}"}
fi

swift build -c release
binary="$(swift build -c release --show-bin-path)/MeetingRecap"
app=.build/MeetingRecap.app
bundle_id=local.meeting-recap.app
cdhash() { codesign -dvvv "$1" 2>&1 | sed -n 's/^CDHash=//p' | head -n 1; }
old_hash=""
[[ -d "$app" ]] && old_hash="$(cdhash "$app")"
rm -rf "$app"
mkdir -p "$app/Contents/MacOS"
cp "$binary" "$app/Contents/MacOS/MeetingRecap"
cat > "$app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key><string>local.meeting-recap.app</string>
    <key>CFBundleName</key><string>MeetingRecap</string>
    <key>CFBundleDisplayName</key><string>Meeting Recap</string>
    <key>CFBundleExecutable</key><string>MeetingRecap</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>0.1</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>26.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Meeting Recap records your microphone so your side of the call is saved in its own file.</string>
</dict>
</plist>
PLIST
codesign --force --sign - --identifier "$bundle_id" "$app"

if [[ "$(cdhash "$app")" != "$old_hash" ]]; then
    if pgrep -xq MeetingRecap; then
        echo "The signature changed, but Meeting Recap is running, so its permissions were left alone. Quit it and run:"
        echo "  tccutil reset ScreenCapture $bundle_id && tccutil reset Microphone $bundle_id"
    else
        tccutil reset ScreenCapture "$bundle_id" >/dev/null
        tccutil reset Microphone "$bundle_id" >/dev/null
        echo "The signature changed, so both permissions were cleared. Press Record and allow both, then quit and reopen the app."
    fi
fi
echo "built $(pwd)/$app"
echo "open it with: open $(pwd)/$app"
