import AppKit
import SwiftUI

@main
struct MeetingRecapApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup("Meeting Recap") {
            ContentView()
                .environment(model)
                .frame(minWidth: 980, minHeight: 640)
                .onAppear {
                    // A bare executable starts behind the terminal; the bundled app does not need this.
                    NSApp.setActivationPolicy(.regular)
                    NSApp.activate(ignoringOtherApps: true)
                }
        }
    }
}
