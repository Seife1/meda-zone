import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../shared/models/field.dart';
import '../../shared/models/slot.dart';
import '../../shared/utils/date_format_utils.dart';

class BookingConfirmScreen extends ConsumerStatefulWidget {
  final String fieldId;
  final String slotId;
  const BookingConfirmScreen({super.key, required this.fieldId, required this.slotId});

  @override
  ConsumerState<BookingConfirmScreen> createState() => _BookingConfirmScreenState();
}

class _BookingConfirmScreenState extends ConsumerState<BookingConfirmScreen> {
  Field? _field;
  Slot? _slot;
  String? _error;
  bool _loading = true;
  bool _expired = false;
  bool _confirming = false;

  /// True once the booking is successfully created OR the user navigates
  /// forward to subscription management intentionally. In either case we
  /// must NOT release the soft reservation from dispose().
  bool _releaseOnDispose = true;

  int _secondsLeft = 300; // 5-minute hold window
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final fieldResp = await ApiClient.dio.get('/fields/${widget.fieldId}');
      _field = Field.fromJson(fieldResp.data as Map<String, dynamic>);

      // Create soft reservation — gives us a 5-minute exclusive hold
      final reserveResp = await ApiClient.dio.post('/slots/${widget.slotId}/reserve');
      _slot = Slot.fromJson(reserveResp.data as Map<String, dynamic>);

      _startTimer();
      if (mounted) setState(() => _loading = false);
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = 'Could not reserve this slot — it may have just been taken.\nPlease go back and try another.';
        });
      }
    }
  }

  void _startTimer() {
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_secondsLeft <= 0) {
        timer.cancel();
        if (mounted) setState(() => _expired = true);
      } else {
        if (mounted) setState(() => _secondsLeft--);
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    // Only release the soft reservation if user didn't complete or forward the flow
    if (_slot != null && !_expired && _releaseOnDispose) {
      ApiClient.dio.delete('/slots/${widget.slotId}/reserve').ignore();
    }
    super.dispose();
  }

  String get _countdown {
    final m = _secondsLeft ~/ 60;
    final s = _secondsLeft % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }

  String _friendlyError(dynamic e) {
    try {
      final data = (e as dynamic).response?.data;
      if (data is Map) {
        final detail = data['detail'];
        if (detail is Map) return detail['message']?.toString() ?? 'Booking failed.';
        if (detail is String) return detail;
      }
    } catch (_) {}
    return 'Booking failed. Please try again.';
  }

  bool _isSubscriptionError(dynamic e) {
    try {
      final status = (e as dynamic).response?.statusCode as int?;
      if (status == 402) return true;
      final detail = (e as dynamic).response?.data?['detail']?.toString() ?? '';
      return detail.toLowerCase().contains('subscription');
    } catch (_) {
      return false;
    }
  }

  /// Confirm the booking by POSTing to /bookings.
  /// On success → navigate to the new booking's detail page.
  /// On subscription error → offer to go to subscription management.
  Future<void> _confirmBooking() async {
    setState(() { _confirming = true; _error = null; });
    try {
      final resp = await ApiClient.dio.post('/bookings', data: {
        'slot_id': widget.slotId,
      });
      final bookingId = resp.data['id'] as String? ?? '';
      // Booking confirmed — do NOT release the slot hold (it's now a booking)
      _releaseOnDispose = false;
      if (mounted) {
        context.go('/bookings/$bookingId');
      }
    } catch (e) {
      if (!mounted) return;
      setState(() => _confirming = false);
      if (_isSubscriptionError(e)) {
        _showSubscriptionRequiredDialog();
      } else {
        setState(() => _error = _friendlyError(e));
      }
    }
  }

  void _showSubscriptionRequiredDialog() {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Subscription Required'),
        content: const Text(
          'You need an active subscription for this field to confirm a booking.\n\n'
          'Head to your subscriptions to activate or pay for one.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              // Keep the slot reservation alive — user may return
              _releaseOnDispose = false;
              context.go('/subscriptions/manage');
            },
            child: const Text('View Subscriptions'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Scaffold(body: Center(child: CircularProgressIndicator()));

    // ── Expired state ─────────────────────────────────────────────────────────
    if (_expired) {
      return Scaffold(
        appBar: const BrandAppBar(),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.timer_off, size: 64, color: AppColors.error),
                const SizedBox(height: 16),
                const Text('Reservation Expired',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                const Text(
                  'Your 5-minute hold on this slot has expired. Please go back and select another slot.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () => context.go('/fields/${widget.fieldId}'),
                  child: const Text('Back to Field'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    // ── Init error (could not reserve slot) ───────────────────────────────────
    if (_error != null && _slot == null) {
      return Scaffold(
        appBar: const BrandAppBar(),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, size: 56, color: AppColors.error),
                const SizedBox(height: 16),
                Text(_error!, textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 15)),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () => context.pop(),
                  child: const Text('Go Back'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final isUrgent = _secondsLeft <= 60;

    // ── Confirm screen ────────────────────────────────────────────────────────
    return Scaffold(
      appBar: BrandAppBar(
        // Fix #6: show field name as subtitle in the AppBar
        bottom: _field != null
            ? PreferredSize(
                preferredSize: const Size.fromHeight(18),
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    _field!.name,
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(context)
                          .appBarTheme
                          .foregroundColor
                          ?.withOpacity(0.65),
                    ),
                  ),
                ),
              )
            : null,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Field info
            if (_field != null) ...[
              Text(_field!.name, style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 4),
              Text(_field!.address, style: Theme.of(context).textTheme.bodySmall),
            ],
            const SizedBox(height: 24),

            // Slot details
            if (_slot != null) ...[
              _Row('Date', formatSlotDate(_slot!.slotDate)),
              _Row('Time', '${formatTime(_slot!.startTime)} – ${formatTime(_slot!.endTime)}'),
              if (_field != null)
                _Row('Price', 'ETB ${_field!.pricePerHour.toStringAsFixed(0)}'),
            ],
            const SizedBox(height: 24),

            // Countdown timer — turns red in the last 60 seconds
            Container(
              padding: const EdgeInsets.symmetric(vertical: 16),
              decoration: BoxDecoration(
                color: (isUrgent ? AppColors.error : AppColors.primaryGreen)
                    .withOpacity(0.08),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: (isUrgent ? AppColors.error : AppColors.primaryGreen)
                      .withOpacity(0.3),
                ),
              ),
              child: Column(
                children: [
                  Text(
                    isUrgent ? 'Hurry! Expires in' : 'Reservation expires in',
                    style: const TextStyle(fontSize: 13),
                  ),
                  Text(
                    _countdown,
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w800,
                      color: isUrgent ? AppColors.error : AppColors.primaryGreen,
                    ),
                  ),
                ],
              ),
            ),

            // Inline error (confirmation failure)
            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.error.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AppColors.error.withOpacity(0.3)),
                ),
                child: Text(_error!,
                    style: const TextStyle(color: AppColors.error, fontSize: 13)),
              ),
            ],

            const Spacer(),

            // Primary CTA
            PrimaryButton(
              label: 'Confirm Booking',
              isLoading: _confirming,
              onPressed: _confirming ? null : _confirmBooking,
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: _confirming ? null : () => context.pop(),
              child: const Text('Cancel'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;
  const _Row(this.label, this.value);

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            SizedBox(
              width: 80,
              child: Text(
                label,
                style: TextStyle(color: Colors.grey[600], fontWeight: FontWeight.w500),
              ),
            ),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
          ],
        ),
      );
}
