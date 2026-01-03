import 'dart:convert';
import 'dart:ffi' as ffi;
import 'dart:io';

import 'package:ffi/ffi.dart';

enum AgentAction {
  micToggle,
  manualInput,
  toggleFallback,
  webSearch,
  calendarView,
  contextView,
  openSettings,
  toggleSilentMode,
}

class AgentSnapshot {
  const AgentSnapshot({
    required this.mode,
    required this.cpuUsage,
    required this.cpuPercent,
    required this.micEnabled,
    required this.silentMode,
    required this.transcript,
  });

  final String mode;
  final double cpuUsage;
  final int cpuPercent;
  final bool micEnabled;
  final bool silentMode;
  final List<String> transcript;

  factory AgentSnapshot.fromJsonString(String input) {
    final decoded = jsonDecode(input) as Map<String, dynamic>;
    return AgentSnapshot(
      mode: decoded['mode'] as String? ?? 'NORMAL',
      cpuUsage: (decoded['cpu_usage'] as num?)?.toDouble() ?? 0.38,
      cpuPercent: (decoded['cpu_percent'] as num?)?.toInt() ?? 38,
      micEnabled: decoded['mic_enabled'] as bool? ?? false,
      silentMode: decoded['silent_mode'] as bool? ?? false,
      transcript: (decoded['transcript'] as List<dynamic>? ?? const [])
          .map((entry) => entry.toString())
          .toList(),
    );
  }
}

abstract class AgentBackend {
  AgentSnapshot snapshot();
  AgentSnapshot handleAction(AgentAction action);
}

class RustAgentBackend implements AgentBackend {
  RustAgentBackend._(this._lib) {
    _snapshot = _lib
        .lookup<ffi.NativeFunction<_AgentSnapshotNative>>('agent_snapshot')
        .asFunction();
    _handleAction = _lib
        .lookup<ffi.NativeFunction<_AgentHandleActionNative>>(
            'agent_handle_action')
        .asFunction();
    _free = _lib
        .lookup<ffi.NativeFunction<_AgentFreeNative>>('agent_free')
        .asFunction();
  }

  final ffi.DynamicLibrary _lib;
  late final _AgentSnapshot _snapshot;
  late final _AgentHandleAction _handleAction;
  late final _AgentFree _free;

  static AgentBackend load() {
    if (!Platform.isLinux) {
      return MockAgentBackend();
    }
    try {
      return RustAgentBackend._(ffi.DynamicLibrary.open(_libraryPath()));
    } catch (_) {
      return MockAgentBackend();
    }
  }

  @override
  AgentSnapshot snapshot() {
    final ptr = _snapshot();
    return _consume(ptr);
  }

  @override
  AgentSnapshot handleAction(AgentAction action) {
    final ptr = _handleAction(action.index);
    return _consume(ptr);
  }

  AgentSnapshot _consume(ffi.Pointer<Utf8> ptr) {
    if (ptr == ffi.nullptr) {
      return const AgentSnapshot(
        mode: 'NORMAL',
        cpuUsage: 0.38,
        cpuPercent: 38,
        micEnabled: false,
        silentMode: false,
        transcript: [],
      );
    }
    final json = ptr.toDartString();
    _free(ptr);
    return AgentSnapshot.fromJsonString(json);
  }

  static String _libraryPath() {
    final override = Platform.environment['AGENT_CORE_LIB'];
    if (override != null && override.isNotEmpty) {
      return override;
    }
    final executableDir = File(Platform.resolvedExecutable).parent;
    final bundledPath = '${executableDir.path}/lib/libagent_core.so';
    if (File(bundledPath).existsSync()) {
      return bundledPath;
    }
    final base = Directory.current.path;
    final releasePath = '$base/native/agent_core/target/release/libagent_core.so';
    if (File(releasePath).existsSync()) {
      return releasePath;
    }
    return '$base/native/agent_core/target/debug/libagent_core.so';
  }
}

class MockAgentBackend implements AgentBackend {
  MockAgentBackend() {
    _snapshot = const AgentSnapshot(
      mode: 'NORMAL',
      cpuUsage: 0.38,
      cpuPercent: 38,
      micEnabled: false,
      silentMode: false,
      transcript: [
        '> Clara: Good morning, Mr. Jackson.',
        "> You: What's the weather in Sommerfeld today?",
        '> Clara: Foggy, but charming.',
      ],
    );
  }

  late AgentSnapshot _snapshot;

  @override
  AgentSnapshot snapshot() => _snapshot;

  @override
  AgentSnapshot handleAction(AgentAction action) {
    final transcript = List<String>.from(_snapshot.transcript);
    switch (action) {
      case AgentAction.micToggle:
        final enabled = !_snapshot.micEnabled;
        _snapshot = _snapshot.copyWith(
          micEnabled: enabled,
          transcript: [
            ...transcript,
            "> System: Mic ${enabled ? "enabled" : "disabled"}",
          ],
        );
        break;
      case AgentAction.manualInput:
        _snapshot = _snapshot.copyWith(
          transcript: [
            ...transcript,
            '> System: Manual input requested.',
          ],
        );
        break;
      case AgentAction.toggleFallback:
        final fallback = _snapshot.mode != 'FALLBACK';
        _snapshot = _snapshot.copyWith(
          mode: fallback ? 'FALLBACK' : 'NORMAL',
          transcript: [
            ...transcript,
            "> Clara: Fallback mode ${fallback ? "enabled" : "disabled"}.",
          ],
        );
        break;
      case AgentAction.webSearch:
        _snapshot = _snapshot.copyWith(
          transcript: [
            ...transcript,
            '> System: Web search triggered.',
          ],
        );
        break;
      case AgentAction.calendarView:
        _snapshot = _snapshot.copyWith(
          transcript: [
            ...transcript,
            '> System: Calendar view opened.',
          ],
        );
        break;
      case AgentAction.contextView:
        _snapshot = _snapshot.copyWith(
          transcript: [
            ...transcript,
            '> System: Context snapshot requested.',
          ],
        );
        break;
      case AgentAction.openSettings:
        _snapshot = _snapshot.copyWith(
          transcript: [
            ...transcript,
            '> System: Settings opened.',
          ],
        );
        break;
      case AgentAction.toggleSilentMode:
        final silent = !_snapshot.silentMode;
        _snapshot = _snapshot.copyWith(
          silentMode: silent,
          transcript: [
            ...transcript,
            "> System: Silent mode ${silent ? "enabled" : "disabled"}",
          ],
        );
        break;
    }
    return _snapshot;
  }
}

extension on AgentSnapshot {
  AgentSnapshot copyWith({
    String? mode,
    double? cpuUsage,
    int? cpuPercent,
    bool? micEnabled,
    bool? silentMode,
    List<String>? transcript,
  }) {
    return AgentSnapshot(
      mode: mode ?? this.mode,
      cpuUsage: cpuUsage ?? this.cpuUsage,
      cpuPercent: cpuPercent ?? this.cpuPercent,
      micEnabled: micEnabled ?? this.micEnabled,
      silentMode: silentMode ?? this.silentMode,
      transcript: transcript ?? this.transcript,
    );
  }
}

typedef _AgentSnapshotNative = ffi.Pointer<Utf8> Function();
typedef _AgentHandleActionNative = ffi.Pointer<Utf8> Function(ffi.Uint32);
typedef _AgentFreeNative = ffi.Void Function(ffi.Pointer<Utf8>);

typedef _AgentSnapshot = ffi.Pointer<Utf8> Function();
typedef _AgentHandleAction = ffi.Pointer<Utf8> Function(int);
typedef _AgentFree = void Function(ffi.Pointer<Utf8>);
