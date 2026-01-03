import 'package:flutter/material.dart';

import 'agent_bridge.dart';

void main() {
  runApp(const ClaraApp());
}

class ClaraApp extends StatefulWidget {
  const ClaraApp({super.key});

  @override
  State<ClaraApp> createState() => _ClaraAppState();
}

class _ClaraAppState extends State<ClaraApp> {
  late final AgentBackend _backend;
  late AgentSnapshot _snapshot;

  @override
  void initState() {
    super.initState();
    _backend = RustAgentBackend.load();
    _snapshot = _backend.snapshot();
  }

  void _handleAction(AgentAction action) {
    setState(() {
      _snapshot = _backend.handleAction(action);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = ThemeData(
      useMaterial3: true,
      fontFamily: 'Georgia',
      fontFamilyFallback: const ['Times New Roman', 'Times', 'serif'],
      colorScheme: const ColorScheme.light(
        primary: Color(0xFF5A3C25),
        secondary: Color(0xFF8B6B46),
        surface: Color(0xFFFFFBF3),
        onSurface: Color(0xFF3C2C1E),
      ),
      scaffoldBackgroundColor: const Color(0xFFF6F0E7),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: Color(0xFF3C2C1E),
        ),
        bodyMedium: TextStyle(
          fontSize: 14,
          color: Color(0xFF3C2C1E),
        ),
      ),
    );

    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Desktop Clara',
      theme: theme,
      home: Scaffold(
        body: SafeArea(
          child: Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Color(0xFFF6F0E7),
                  Color(0xFFF1E7D8),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                HeaderBar(snapshot: _snapshot),
                const Divider(height: 24, color: Color(0xFF7B5E45)),
                Expanded(child: TranscriptPanel(snapshot: _snapshot)),
                const Divider(height: 24, color: Color(0xFF7B5E45)),
                ButtonBarPanel(onAction: _handleAction),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class HeaderBar extends StatelessWidget {
  const HeaderBar({super.key, required this.snapshot});

  final AgentSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final cameo = _HeaderBox(
      child: Text(
        'ClaraGPT Cameo',
        style: Theme.of(context).textTheme.bodyMedium,
      ),
    );

    final mode = _HeaderBox(
      child: Text(
        'Mode: ${snapshot.mode}',
        style: Theme.of(context).textTheme.bodyMedium,
      ),
    );

    final cpu = _HeaderBox(
      child: Row(
        children: [
          const Text('CPU Usage:'),
          const SizedBox(width: 8),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: snapshot.cpuUsage,
                minHeight: 10,
                backgroundColor: const Color(0xFFE3D7C7),
                valueColor: const AlwaysStoppedAnimation<Color>(
                  Color(0xFF7B5E45),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text('${snapshot.cpuPercent}%'),
        ],
      ),
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 720) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(child: cameo),
                  const SizedBox(width: 12),
                  Expanded(child: mode),
                ],
              ),
              const SizedBox(height: 12),
              cpu,
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            cameo,
            const SizedBox(width: 12),
            Expanded(child: cpu),
            const SizedBox(width: 12),
            mode,
          ],
        );
      },
    );
  }
}

class TranscriptPanel extends StatelessWidget {
  const TranscriptPanel({super.key, required this.snapshot});

  final AgentSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '📜 Transcript Log (Scrollable)',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Expanded(
            child: Scrollbar(
              child: ListView.separated(
                itemCount: snapshot.transcript.length,
                separatorBuilder: (_, __) => const SizedBox(height: 6),
                itemBuilder: (context, index) {
                  return Text(snapshot.transcript[index]);
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ButtonBarPanel extends StatelessWidget {
  const ButtonBarPanel({super.key, required this.onAction});

  final void Function(AgentAction) onAction;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final panelWidth =
            (constraints.maxWidth - 24).clamp(0.0, double.infinity) as double;
        if (constraints.maxWidth < 720) {
          return _Panel(
            child: Wrap(
              spacing: 12,
              runSpacing: 12,
              children: _actionButtons(context, 2, panelWidth),
            ),
          );
        }

        return _Panel(
          child: Column(
            children: [
              Row(
                children: _actionButtons(context, 4, panelWidth).sublist(0, 4),
              ),
              const SizedBox(height: 12),
              Row(
                children: _actionButtons(context, 4, panelWidth).sublist(4, 8),
              ),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _actionButtons(
      BuildContext context, int columns, double panelWidth) {
    final buttons = [
      _ActionButton(
        label: '🎙️ Mic Toggle',
        action: AgentAction.micToggle,
        onAction: onAction,
      ),
      _ActionButton(
        label: '⌨️ Manual Input',
        action: AgentAction.manualInput,
        onAction: onAction,
      ),
      _ActionButton(
        label: '🕯️ Fallback',
        action: AgentAction.toggleFallback,
        onAction: onAction,
      ),
      _ActionButton(
        label: '🔍 Web Search',
        action: AgentAction.webSearch,
        onAction: onAction,
      ),
      _ActionButton(
        label: '📅 Calendar',
        action: AgentAction.calendarView,
        onAction: onAction,
      ),
      _ActionButton(
        label: '🧠 Context',
        action: AgentAction.contextView,
        onAction: onAction,
      ),
      _ActionButton(
        label: '🛠️ Settings',
        action: AgentAction.openSettings,
        onAction: onAction,
      ),
      _ActionButton(
        label: '🛑 Silent Mode',
        action: AgentAction.toggleSilentMode,
        onAction: onAction,
      ),
    ];

    if (columns == 4) {
      return buttons
          .map(
            (button) => Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 6),
                child: button,
              ),
            ),
          )
          .toList();
    }

    final width = (panelWidth - (12 * (columns - 1))) / columns;
    return buttons
        .map((button) => SizedBox(width: width, child: button))
        .toList();
  }
}

class _HeaderBox extends StatelessWidget {
  const _HeaderBox({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBF3),
        border: Border.all(color: const Color(0xFF7B5E45)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: child,
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBF3),
        border: Border.all(color: const Color(0xFF7B5E45)),
        borderRadius: BorderRadius.circular(8),
        boxShadow: const [
          BoxShadow(
            color: Color(0x1A000000),
            blurRadius: 6,
            offset: Offset(0, 3),
          ),
        ],
      ),
      child: child,
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.action,
    required this.onAction,
  });

  final String label;
  final AgentAction action;
  final void Function(AgentAction) onAction;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 14),
        backgroundColor: const Color(0xFFE9E0D0),
        foregroundColor: const Color(0xFF3C2C1E),
        side: const BorderSide(color: Color(0xFF7B5E45)),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
      ),
      onPressed: () => onAction(action),
      child: Text(label, textAlign: TextAlign.center),
    );
  }
}
