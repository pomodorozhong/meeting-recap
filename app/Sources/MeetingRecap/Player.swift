import AVFoundation
import Foundation
import Observation

/// Plays a recording's two tracks together from one position.
@MainActor @Observable final class Player {
    private(set) var isPlaying = false
    private(set) var position: Double = 0
    private(set) var duration: Double = 0
    private var players: [AVAudioPlayer] = []
    private var timer: Timer?

    func load(folder: URL) {
        stop()
        players = ["system.m4a", "mic.m4a"].compactMap { try? AVAudioPlayer(contentsOf: folder.appendingPathComponent($0)) }
        players.forEach { $0.prepareToPlay() }
        duration = players.map(\.duration).max() ?? 0
        position = 0
    }

    func toggle() { isPlaying ? pause() : play() }

    func play() {
        guard !players.isEmpty else { return }
        if position >= duration - 0.05 { position = 0 }
        // Start both at one device time so the tracks stay on one timeline.
        let start = players[0].deviceCurrentTime + 0.1
        for player in players {
            player.currentTime = min(position, player.duration)
            player.play(atTime: start)
        }
        isPlaying = true
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.update() }
        }
    }

    func pause() {
        players.forEach { $0.pause() }
        isPlaying = false
        timer?.invalidate()
    }

    func stop() {
        players.forEach { $0.stop() }
        players = []
        isPlaying = false
        position = 0
        duration = 0
        timer?.invalidate()
    }

    /// Jumps to a fraction (0...1) of the recording, keeping the play state.
    func seek(to fraction: Double) {
        position = min(max(fraction, 0), 1) * duration
        if isPlaying {
            play()
        } else {
            players.forEach { $0.currentTime = min(position, $0.duration) }
        }
    }

    private func update() {
        guard isPlaying else { return }
        let positions = players.filter(\.isPlaying).map(\.currentTime)
        if let latest = positions.max() {
            position = latest
        } else if players.allSatisfy({ !$0.isPlaying }) {
            pause()
            position = duration
        }
    }
}
