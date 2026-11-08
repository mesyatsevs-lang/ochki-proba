#!/usr/bin/env python3
"""Патчи к примеру Meta CameraAccess для пробы ochki-proba.

Запуск: python3 patches/apply.py <путь к samples/CameraAccess>
1) уход в фон не закрывает сессию и поток;
2) журнал SpikeLog (кадры, заряд, тепло, состояние приложения, события);
3) Info.plist: папка Documents видна в «Файлах», имя приложения «Очки проба».
Каждая замена проверяется на ровно одно совпадение: изменился пример — скрипт падает, а не молчит.
"""
import pathlib
import plistlib
import sys

root = pathlib.Path(sys.argv[1])
vm_path = root / "CameraAccess" / "ViewModels" / "CameraViewModel.swift"
src = vm_path.read_text(encoding="utf-8")


def rep(old: str, new: str) -> None:
    global src
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"ожидалось 1 совпадение, найдено {n}: {old[:70]!r}")
    src = src.replace(old, new)


# 1. Фон: не закрывать сессию.
rep(
    """  private func handleDidEnterBackground() {
    guard hasSession, hasStream, sessionState != .stopping else { return }

    beginBackgroundStopErrorSuppression()
    endSession()
  }""",
    """  private func handleDidEnterBackground() {
    // SPIKE (ochki-proba): сессию и поток в фоне не закрываем, меряем, сколько они живут.
    SpikeLog.shared.event("didEnterBackground session=\\(hasSession) stream=\\(hasStream) recording=\\(isRecording)")
  }""",
)

# 2. Счётчик кадров.
rep(
    "      self.appendVideoFrame(frame)\n",
    "      self.appendVideoFrame(frame)\n      SpikeLog.shared.frame()\n",
)

# 3. События потока, сессии, ошибок, записи.
rep(
    "  private func handleStreamStateChange(_ state: StreamState) {\n    streamState = state\n",
    "  private func handleStreamStateChange(_ state: StreamState) {\n    SpikeLog.shared.event(\"stream \\(state)\")\n    streamState = state\n",
)
rep(
    "  private func handleSessionStateChange(_ state: DeviceSessionState) {\n    sessionState = state\n",
    "  private func handleSessionStateChange(_ state: DeviceSessionState) {\n    SpikeLog.shared.event(\"session \\(state)\")\n    sessionState = state\n",
)
rep(
    "  private func handleStreamError(_ error: StreamError) {\n",
    "  private func handleStreamError(_ error: StreamError) {\n    SpikeLog.shared.event(\"streamError \\(error)\")\n",
)
rep(
    "  private func handleSessionError(_ error: DeviceSessionError) {\n",
    "  private func handleSessionError(_ error: DeviceSessionError) {\n    SpikeLog.shared.event(\"sessionError \\(error)\")\n",
)
rep(
    "  func toggleRecording() {\n",
    "  func toggleRecording() {\n    SpikeLog.shared.event(\"toggleRecording wasRecording=\\(isRecording)\")\n",
)

# 4. Сам журнал — дописывается в конец того же файла, чтобы не трогать project.pbxproj.
src += (pathlib.Path(__file__).parent / "SpikeLog.swift.txt").read_text(encoding="utf-8")
vm_path.write_text(src, encoding="utf-8")

# 5. Info.plist.
plist_path = root / "CameraAccess" / "Info.plist"
info = plistlib.loads(plist_path.read_bytes())
info["UIFileSharingEnabled"] = True
info["LSSupportsOpeningDocumentsInPlace"] = True
info["CFBundleDisplayName"] = "Очки проба"
plist_path.write_bytes(plistlib.dumps(info))

print("патчи применены:", vm_path, plist_path)
