import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

void main() {
  runApp(const BasicChatApp());
}

class BasicChatApp extends StatelessWidget {
  const BasicChatApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Archive-AI Chat',
      theme: ThemeData(
        primarySwatch: Colors.deepPurple,
        visualDensity: VisualDensity.adaptivePlatformDensity,
        useMaterial3: true,
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<Map<String, String>> _messages = [];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _isLoading = false;

  // Voice functionality
  final AudioRecorder _audioRecorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();
  bool _isRecording = false;
  String? _recordingPath;

  // Configuration
  static const String _apiBaseUrl = 'http://localhost:8081';

  @override
  void initState() {
    super.initState();
    _messages.add({
      'sender': 'Agent',
      'text': 'Hello! I am Archive-AI. How can I help you today?',
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _handleSubmitted(String text) async {
    _textController.clear();
    if (text.trim().isEmpty) return;

    setState(() {
      _messages.add({'sender': 'User', 'text': text});
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      final response = await http.post(
        Uri.parse('$_apiBaseUrl/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'message': text}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final agentResponse = data['response'] ?? 'No response received.';

        if (mounted) {
          setState(() {
            _messages.add({
              'sender': 'Agent',
              'text': agentResponse,
            });
            _isLoading = false;
          });
        }
      } else {
        if (mounted) {
          setState(() {
            _messages.add({
              'sender': 'System',
              'text': 'Error: Server returned status code ${response.statusCode}',
            });
            _isLoading = false;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _messages.add({
            'sender': 'System',
            'text': 'Connection Error: $e\n\nEnsure the backend is running at $_apiBaseUrl',
          });
          _isLoading = false;
        });
      }
    }
    _scrollToBottom();
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      // Stop recording
      final path = await _audioRecorder.stop();
      if (path != null) {
        setState(() {
          _recordingPath = path;
          _isRecording = false;
        });
        // Automatically transcribe
        await _transcribeAudio(path);
      }
    } else {
      // Start recording
      if (await _audioRecorder.hasPermission()) {
        final tempDir = await getTemporaryDirectory();
        final filePath = '${tempDir.path}/recording_${DateTime.now().millisecondsSinceEpoch}.m4a';

        await _audioRecorder.start(
          const RecordConfig(encoder: AudioEncoder.aacLc),
          path: filePath,
        );

        setState(() {
          _isRecording = true;
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Microphone permission denied')),
          );
        }
      }
    }
  }

  Future<void> _transcribeAudio(String audioPath) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('$_apiBaseUrl/voice/transcribe'),
      );

      request.files.add(await http.MultipartFile.fromPath('audio', audioPath));

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final transcribedText = data['text'] ?? '';

        if (transcribedText.isNotEmpty) {
          _textController.text = transcribedText;
          // Automatically send the transcribed text
          await _handleSubmitted(transcribedText);
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Transcription failed: ${response.statusCode}')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Transcription error: $e')),
        );
      }
    } finally {
      setState(() {
        _isLoading = false;
      });

      // Clean up recording file
      try {
        await File(audioPath).delete();
      } catch (_) {}
    }
  }

  Future<void> _speakText(String text) async {
    try {
      final response = await http.post(
        Uri.parse('$_apiBaseUrl/voice/synthesize'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': text}),
      );

      if (response.statusCode == 200) {
        // Save audio to temp file
        final tempDir = await getTemporaryDirectory();
        final audioFile = File('${tempDir.path}/speech_${DateTime.now().millisecondsSinceEpoch}.wav');
        await audioFile.writeAsBytes(response.bodyBytes);

        // Play audio
        await _audioPlayer.play(DeviceFileSource(audioFile.path));

        // Clean up after playback
        _audioPlayer.onPlayerComplete.listen((_) async {
          try {
            await audioFile.delete();
          } catch (_) {}
        });
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Speech synthesis failed: ${response.statusCode}')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Speech synthesis error: $e')),
        );
      }
    }
  }

  @override
  void dispose() {
    _audioRecorder.dispose();
    _audioPlayer.dispose();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Archive-AI Client'),
        backgroundColor: Colors.deepPurple.shade100,
      ),
      body: Column(
        children: <Widget>[
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16.0),
              itemCount: _messages.length,
              itemBuilder: (_, int index) {
                final message = _messages[index];
                final sender = message['sender'];
                final text = message['text']!;
                
                final isUser = sender == 'User';
                final isSystem = sender == 'System';

                Color bubbleColor;
                Color textColor;
                Alignment alignment;

                if (isUser) {
                  bubbleColor = Colors.deepPurple;
                  textColor = Colors.white;
                  alignment = Alignment.centerRight;
                } else if (isSystem) {
                  bubbleColor = Colors.red.shade100;
                  textColor = Colors.red.shade900;
                  alignment = Alignment.center;
                } else {
                  bubbleColor = Colors.grey.shade200;
                  textColor = Colors.black87;
                  alignment = Alignment.centerLeft;
                }

                return Align(
                  alignment: alignment,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4.0),
                    padding: const EdgeInsets.all(12.0),
                    constraints: BoxConstraints(
                      maxWidth: MediaQuery.of(context).size.width * 0.75,
                    ),
                    decoration: BoxDecoration(
                      color: bubbleColor,
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(12),
                        topRight: const Radius.circular(12),
                        bottomLeft: isUser ? const Radius.circular(12) : Radius.zero,
                        bottomRight: isUser ? Radius.zero : const Radius.circular(12),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (!isUser && !isSystem)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 4.0),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  sender!,
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: textColor.withOpacity(0.7),
                                  ),
                                ),
                                IconButton(
                                  icon: const Icon(Icons.volume_up, size: 16),
                                  onPressed: () => _speakText(text),
                                  color: Colors.blue,
                                  tooltip: 'Play as audio',
                                  padding: EdgeInsets.zero,
                                  constraints: const BoxConstraints(),
                                ),
                              ],
                            ),
                          ),
                        MarkdownBody(
                          data: text,
                          styleSheet: MarkdownStyleSheet(
                            p: TextStyle(color: textColor),
                            code: TextStyle(
                              backgroundColor: isUser ? Colors.deepPurple.shade700 : Colors.grey.shade300,
                              color: isUser ? Colors.white : Colors.black87,
                              fontFamily: 'monospace',
                            ),
                            codeblockDecoration: BoxDecoration(
                              color: isUser ? Colors.deepPurple.shade700 : Colors.grey.shade300,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: LinearProgressIndicator(),
            ),
          const Divider(height: 1.0),
          Container(
            decoration: BoxDecoration(color: Theme.of(context).cardColor),
            child: _buildTextComposer(),
          ),
        ],
      ),
    );
  }

  Widget _buildTextComposer() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 8.0),
      child: Row(
        children: <Widget>[
          Flexible(
            child: TextField(
              controller: _textController,
              onSubmitted: _isLoading ? null : _handleSubmitted,
              decoration: const InputDecoration.collapsed(
                hintText: 'Type a message...',
              ),
              enabled: !_isLoading,
            ),
          ),
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 4.0),
            child: IconButton(
              icon: Icon(_isRecording ? Icons.stop : Icons.mic),
              onPressed: _isLoading ? null : _toggleRecording,
              color: _isRecording ? Colors.red : Colors.green,
              tooltip: _isRecording ? 'Stop recording' : 'Record voice',
            ),
          ),
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 4.0),
            child: IconButton(
              icon: const Icon(Icons.send),
              onPressed: _isLoading ? null : () => _handleSubmitted(_textController.text),
              color: Theme.of(context).primaryColor,
            ),
          ),
        ],
      ),
    );
  }
}
