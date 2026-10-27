import 'dart:async';
import 'dart:convert';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../core/api_client.dart';
import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../shared/models/field.dart';
import '../../shared/models/slot.dart';
import '../../shared/utils/date_format_utils.dart';

class FieldDetailScreen extends ConsumerStatefulWidget {
  final String fieldId;
  const FieldDetailScreen({super.key, required this.fieldId});

  @override
  ConsumerState<FieldDetailScreen> createState() => _FieldDetailScreenState();
}

class _FieldDetailScreenState extends ConsumerState<FieldDetailScreen> {
  Field? _field;
  List<Slot> _slots = [];
  List<Map<String, dynamic>> _reviews = [];
  bool _loading = true;
  String? _error;

  WebSocketChannel? _channel;
  int _reconnectDelay = AppConstants.wsReconnectInitialMs;
  bool _disposed = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final results = await Future.wait([
        ApiClient.dio.get('/fields/${widget.fieldId}'),
        ApiClient.dio.get('/fields/${widget.fieldId}/slots'),
        ApiClient.dio.get('/fields/${widget.fieldId}/reviews', queryParameters: {'page': 1, 'page_size': 5}),
      ]);
      if (!mounted) return;
      setState(() {
        _field = Field.fromJson(results[0].data as Map<String, dynamic>);
        _slots = (results[1].data as List<dynamic>)
            .map((j) => Slot.fromJson(j as Map<String, dynamic>))
            .toList();
        _reviews = (results[2].data as List<dynamic>)
            .cast<Map<String, dynamic>>();
        _loading = false;
      });
      _connectWs();
    } catch (e) {
      if (mounted) setState(() { _loading = false; _error = e.toString(); });
    }
  }

  void _connectWs() {
    if (_disposed) return;
    try {
      final uri = Uri.parse('${AppConstants.wsBaseUrl}/ws/fields/${widget.fieldId}');
      _channel = WebSocketChannel.connect(uri);
      _channel!.stream.listen(
        _onWsMessage,
        onDone: _onWsDone,
        onError: (_) => _onWsDone(),
        cancelOnError: false,
      );
      _reconnectDelay = AppConstants.wsReconnectInitialMs;
    } catch (_) {
      _onWsDone();
    }
  }

  void _onWsMessage(dynamic raw) {
    try {
      final msg = jsonDecode(raw as String) as Map<String, dynamic>;
      if (msg['type'] == 'slot_update') {
        final slotId = msg['slot_id'] as String;
        final status = msg['status'] as String;
        if (!mounted) return;
        setState(() {
          _slots = _slots.map((s) {
            if (s.id == slotId) {
              return Slot(
                id: s.id, fieldId: s.fieldId,
                slotDate: msg['slot_date'] as String? ?? s.slotDate,
                startTime: msg['start_time'] as String? ?? s.startTime,
                endTime: msg['end_time'] as String? ?? s.endTime,
                durationMinutes: s.durationMinutes,
                status: status,
              );
            }
            return s;
          }).toList();
        });
      }
    } catch (_) {}
  }

  void _onWsDone() {
    if (_disposed) return;
    Future.delayed(Duration(milliseconds: _reconnectDelay), () {
      if (!_disposed) {
        _reconnectDelay = (_reconnectDelay * 2).clamp(
            AppConstants.wsReconnectInitialMs, AppConstants.wsReconnectMaxMs);
        _connectWs();
      }
    });
  }

  @override
  void dispose() {
    _disposed = true;
    _channel?.sink.close();
    super.dispose();
  }

  Future<void> _watchField() async {
    try {
      await ApiClient.dio.post('/notifications/watch/${widget.fieldId}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("You'll be notified when a slot opens")));
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));
    if (_error != null) return Scaffold(
        appBar: const BrandAppBar(),
        body: Center(child: Text(_error!, style: const TextStyle(color: AppColors.error))));
    if (_field == null) return const Scaffold(body: Center(child: Text('Field not found')));

    final field = _field!;
    final hasAvailable = _slots.any((s) => s.status == 'available');

    // Group slots by date
    final Map<String, List<Slot>> slotsByDate = {};
    for (final s in _slots) {
      slotsByDate.putIfAbsent(s.slotDate, () => []).add(s);
    }

    return Scaffold(
      appBar: BrandAppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications_outlined),
            onPressed: _watchField,
            tooltip: 'Notify me when available',
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Photos
            if (field.photoUrls.isNotEmpty)
              SizedBox(
                height: 200,
                child: ListView.builder(
                  scrollDirection: Axis.horizontal,
                  itemCount: field.photoUrls.length,
                  itemBuilder: (_, i) => Padding(
                    padding: const EdgeInsets.only(right: 2),
                    child: CachedNetworkImage(
                      imageUrl: field.photoUrls[i],
                      width: 300, fit: BoxFit.cover,
                      placeholder: (_, __) => Container(width: 300, color: Colors.grey[200]),
                      errorWidget: (_, __, ___) => Container(width: 300, color: Colors.grey[200],
                          child: const Icon(Icons.sports_soccer, size: 48, color: Colors.grey)),
                    ),
                  ),
                ),
              )
            else
              Container(
                height: 160,
                color: AppColors.darkGreen.withOpacity(0.15),
                child: const Center(child: Text('⚽', style: TextStyle(fontSize: 64))),
              ),

            Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Header
                  Text(field.name, style: Theme.of(context).textTheme.headlineMedium),
                  const SizedBox(height: 4),
                  Text(field.address, style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 12),

                  // Info chips
                  Wrap(
                    spacing: 8, runSpacing: 6,
                    children: [
                      _Chip(Icons.grass, field.surfaceType),
                      if (field.fieldSize != null) _Chip(Icons.grid_on, field.fieldSize!),
                      _Chip(Icons.attach_money, 'ETB ${field.pricePerHour.toStringAsFixed(0)}/hr'),
                      if (field.averageRating > 0)
                        _Chip(Icons.star, field.averageRating.toStringAsFixed(1),
                            color: const Color(0xFFFFD700)),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Amenities
                  _AmenitiesRow(field.amenities),
                  const SizedBox(height: 20),
                  const Divider(),
                  const SizedBox(height: 16),

                  // 7-day slot calendar
                  Text('Availability', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  if (!hasAvailable) ...[
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.grey[100],
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Column(
                        children: [
                          const Text('No availability this week',
                              style: TextStyle(fontWeight: FontWeight.w600)),
                          const SizedBox(height: 8),
                          TextButton.icon(
                            onPressed: _watchField,
                            icon: const Icon(Icons.notifications_outlined, color: AppColors.primaryGreen),
                            label: const Text('Notify me when available',
                                style: TextStyle(color: AppColors.primaryGreen)),
                          ),
                        ],
                      ),
                    ),
                  ] else
                    ...slotsByDate.entries.map((entry) => _DaySlots(
                          date: entry.key,
                          slots: entry.value,
                          onSlotTap: (slot) {
                            if (slot.status == 'available') {
                              context.go('/fields/${widget.fieldId}/book/${slot.id}');
                            }
                          },
                        )),

                  const SizedBox(height: 20),
                  const Divider(),
                  const SizedBox(height: 16),

                  // Reviews
                  Row(
                    children: [
                      Text('Reviews', style: Theme.of(context).textTheme.titleLarge),
                      const Spacer(),
                      if (field.reviewCount > 0)
                        Text('${field.reviewCount} total',
                            style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                  const SizedBox(height: 12),
                  if (_reviews.isEmpty)
                    const Text('No reviews yet',
                        style: TextStyle(color: AppColors.textMuted))
                  else
                    ..._reviews.map((r) => _ReviewTile(r)),

                  const SizedBox(height: 24),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color? color;
  const _Chip(this.icon, this.label, {this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: (color ?? AppColors.primaryGreen).withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: color ?? AppColors.primaryGreen),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600,
            color: color ?? AppColors.darkNavy)),
      ]),
    );
  }
}

class _AmenitiesRow extends StatelessWidget {
  final Map<String, dynamic> amenities;
  const _AmenitiesRow(this.amenities);

  @override
  Widget build(BuildContext context) {
    final items = <Widget>[];
    void add(String key, IconData icon, String label) {
      final val = amenities[key];
      final has = val == true || val == 'true';
      items.add(Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 24, color: has ? AppColors.primaryGreen : Colors.grey[300]),
        const SizedBox(height: 4),
        Text(label, style: TextStyle(fontSize: 10, color: has ? AppColors.darkNavy : Colors.grey)),
      ]));
    }
    add('lighting', Icons.lightbulb_outline, 'Lighting');
    add('changing_rooms', Icons.shower, 'Changing');
    add('parking', Icons.local_parking, 'Parking');
    add('water', Icons.water_drop_outlined, 'Water');
    return Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: items);
  }
}

class _DaySlots extends StatelessWidget {
  final String date;
  final List<Slot> slots;
  final void Function(Slot) onSlotTap;
  const _DaySlots({required this.date, required this.slots, required this.onSlotTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(formatSlotDate(date),
            style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 6, runSpacing: 6,
          children: slots.map((s) {
            Color bg;
            Color text;
            switch (s.status) {
              case 'available': bg = AppColors.primaryGreen; text = Colors.white; break;
              case 'booked': bg = Colors.grey[300]!; text = Colors.grey[600]!; break;
              default: bg = Colors.grey[200]!; text = Colors.grey[400]!;
            }
            return GestureDetector(
              onTap: () => onSlotTap(s),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(8)),
                child: Text('${formatTime(s.startTime)}–${formatTime(s.endTime)}',
                    style: TextStyle(fontSize: 12, color: text, fontWeight: FontWeight.w600)),
              ),
            );
          }).toList(),
        ),
      ]),
    );
  }
}

class _ReviewTile extends StatelessWidget {
  final Map<String, dynamic> review;
  const _ReviewTile(this.review);

  @override
  Widget build(BuildContext context) {
    final rating = review['rating'] as int? ?? 0;
    final text = review['review_text'] as String?;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: List.generate(5, (i) => Icon(
            i < rating ? Icons.star : Icons.star_border,
            size: 16, color: const Color(0xFFFFD700)))),
        if (text != null && text.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(text, style: Theme.of(context).textTheme.bodySmall),
        ],
        const Divider(height: 16),
      ]),
    );
  }
}
