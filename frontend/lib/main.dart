import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';

// Set at build: flutter build web --dart-define=API_URL=https://...
const String apiUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://localhost:8080',
);

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Research Assistant',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.dark(
          primary: const Color(0xFF6366F1),
          surface: const Color(0xFF16161A),
          error: const Color(0xFFEF4444),
          onPrimary: Colors.white,
          onSurface: const Color(0xFFE4E4E7),
          onSurfaceVariant: const Color(0xFFA1A1AA),
        ),
        fontFamily: 'DM Sans',
      ),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _queryController = TextEditingController();
  final _scrollController = ScrollController();
  bool _loading = false;
  String _answer = '';
  List<SourceItem> _sources = [];
  String? _error;

  Future<void> _submit() async {
    final question = _queryController.text.trim();
    if (question.isEmpty) return;
    setState(() {
      _loading = true;
      _error = null;
      _answer = '';
      _sources = [];
    });
    try {
      final base = apiUrl.endsWith('/') ? apiUrl.substring(0, apiUrl.length - 1) : apiUrl;
      final res = await http.post(
        Uri.parse('$base/query'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'question': question}),
      );
      if (res.statusCode >= 400) {
        throw Exception(res.body.isNotEmpty ? res.body : 'Request failed');
      }
      final data = jsonDecode(res.body) as Map<String, dynamic>;
      setState(() {
        _answer = data['answer'] as String? ?? '';
        _sources = (data['sources'] as List<dynamic>?)
                ?.map((e) => SourceItem.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [];
      });
    } catch (e) {
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _queryController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0F),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 24),
                  Text(
                    'AI Research Assistant',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.02,
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Ask a question — get an answer with sources.',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _queryController,
                          enabled: !_loading,
                          decoration: InputDecoration(
                            hintText: 'Ask anything...',
                            filled: true,
                            fillColor: const Color(0xFF16161A),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: Color(0xFF2A2A2E)),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: Color(0xFF2A2A2E)),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(10),
                              borderSide: const BorderSide(color: Color(0xFF6366F1), width: 1.5),
                            ),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                          ),
                          onSubmitted: (_) => _submit(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: _loading ? null : _submit,
                        style: FilledButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        child: Text(_loading ? 'Searching…' : 'Search'),
                      ),
                    ],
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                        border: Border.all(color: const Color(0xFFEF4444)),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(_error!, style: const TextStyle(color: Color(0xFFFCA5A5))),
                    ),
                  ],
                  if (_answer.isNotEmpty) ...[
                    const SizedBox(height: 32),
                    Expanded(
                      child: SingleChildScrollView(
                        controller: _scrollController,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            _Panel(
                              title: 'Answer',
                              child: _AnswerBody(
                                answer: _answer,
                                sources: _sources,
                              ),
                            ),
                            if (_sources.isNotEmpty) ...[
                              const SizedBox(height: 24),
                              _Panel(
                                title: 'Sources',
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: _sources
                                      .map((s) => Padding(
                                            padding: const EdgeInsets.symmetric(vertical: 6),
                                            child: Row(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Text(
                                                  '[${s.index}]',
                                                  style: TextStyle(
                                                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                                                    fontFamily: 'monospace',
                                                    fontSize: 13,
                                                  ),
                                                ),
                                                const SizedBox(width: 8),
                                                Expanded(
                                                  child: InkWell(
                                                    onTap: () {
                                                      final uri = Uri.tryParse(s.url);
                                                      if (uri != null) {
                                                        launchUrl(uri, mode: LaunchMode.externalApplication);
                                                      }
                                                    },
                                                    child: Text(
                                                      s.title?.isNotEmpty == true ? s.title! : s.url,
                                                      style: const TextStyle(
                                                        color: Color(0xFF6366F1),
                                                        decoration: TextDecoration.underline,
                                                      ),
                                                    ),
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ))
                                      .toList(),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  ],
                  const Spacer(),
                  Center(
                    child: Text(
                      'Powered by Gemini & Vertex AI',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  final String title;
  final Widget child;

  const _Panel({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF16161A),
        border: Border.all(color: const Color(0xFF2A2A2E)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title.toUpperCase(),
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  letterSpacing: 0.8,
                ),
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _AnswerBody extends StatelessWidget {
  final String answer;
  final List<SourceItem> sources;

  const _AnswerBody({required this.answer, required this.sources});

  @override
  Widget build(BuildContext context) {
    final parts = _splitAnswer(answer);
    return RichText(
      text: TextSpan(
        style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: Theme.of(context).colorScheme.onSurface,
              height: 1.6,
            ),
        children: parts.map((part) {
          if (part.isCitation) {
            final idx = int.tryParse(part.text) ?? 0;
            SourceItem? src;
            for (final s in sources) {
              if (s.index == idx) {
                src = s;
                break;
              }
            }
            if (src != null && src.url.isNotEmpty) {
              final sourceUrl = src.url;
              return WidgetSpan(
                alignment: PlaceholderAlignment.baseline,
                baseline: TextBaseline.alphabetic,
                child: InkWell(
                  onTap: () {
                    final uri = Uri.tryParse(sourceUrl);
                    if (uri != null) {
                      launchUrl(uri, mode: LaunchMode.externalApplication);
                    }
                  },
                  child: Text(
                    '[${part.text}]',
                    style: const TextStyle(
                      color: Color(0xFF6366F1),
                      fontWeight: FontWeight.w600,
                      decoration: TextDecoration.underline,
                    ),
                  ),
                ),
              );
            }
            return TextSpan(
              text: '[${part.text}]',
              style: const TextStyle(color: Color(0xFF6366F1), fontWeight: FontWeight.w600),
            );
          }
          return TextSpan(text: part.text);
        }).toList(),
      ),
    );
  }

  static List<_AnswerPart> _splitAnswer(String text) {
    final re = RegExp(r'(\[\d+\])');
    final list = <_AnswerPart>[];
    int start = 0;
    for (final m in re.allMatches(text)) {
      if (m.start > start) list.add(_AnswerPart(text.substring(start, m.start), false));
      list.add(_AnswerPart(m.group(1)!.replaceAll(RegExp(r'[\[\]]'), ''), true));
      start = m.end;
    }
    if (start < text.length) list.add(_AnswerPart(text.substring(start), false));
    return list;
  }
}

class _AnswerPart {
  final String text;
  final bool isCitation;
  _AnswerPart(this.text, this.isCitation);
}

class SourceItem {
  final int index;
  final String url;
  final String? title;

  SourceItem({required this.index, required this.url, this.title});

  static SourceItem fromJson(Map<String, dynamic> json) {
    return SourceItem(
      index: (json['index'] as num?)?.toInt() ?? 0,
      url: json['url'] as String? ?? '',
      title: json['title'] as String?,
    );
  }
}
