class Subscription {
  final String id;
  final String playerId;
  final String fieldId;
  final String proposedBy;
  final List<String> recurringDays;
  final String sessionStartTime;
  final double sessionDurationHours;
  final String tier; // 1_month | 2_months | 3_months
  final int totalSessions;
  final double totalPrice;
  final String status; // pending_payment | active | expired | cancelled
  final String? startDate;
  final String? expiryDate;
  final String? paymentProvider;
  final String createdAt;

  const Subscription({
    required this.id,
    required this.playerId,
    required this.fieldId,
    required this.proposedBy,
    required this.recurringDays,
    required this.sessionStartTime,
    required this.sessionDurationHours,
    required this.tier,
    required this.totalSessions,
    required this.totalPrice,
    required this.status,
    this.startDate,
    this.expiryDate,
    this.paymentProvider,
    required this.createdAt,
  });

  static double _toDouble(dynamic v) {
    if (v == null) return 0.0;
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v) ?? 0.0;
    return 0.0;
  }

  factory Subscription.fromJson(Map<String, dynamic> j) => Subscription(
        id: j['id'] as String,
        playerId: j['player_id'] as String,
        fieldId: j['field_id'] as String,
        proposedBy: j['proposed_by'] as String,
        recurringDays: (j['recurring_days'] as List<dynamic>? ?? [])
            .map((e) => e as String)
            .toList(),
        sessionStartTime: j['session_start_time'] as String,
        sessionDurationHours:
            _toDouble(j['session_duration_hours']),
        tier: j['tier'] as String,
        totalSessions: j['total_sessions'] as int,
        totalPrice: _toDouble(j['total_price']),
        status: j['status'] as String? ?? 'pending_payment',
        startDate: j['start_date'] as String?,
        expiryDate: j['expiry_date'] as String?,
        paymentProvider: j['payment_provider'] as String?,
        createdAt: j['created_at'] as String,
      );

  /// Days remaining until the subscription expires.
  /// Returns null if [expiryDate] is not set.
  int? get daysRemaining {
    if (expiryDate == null) return null;
    final expiry = DateTime.tryParse(expiryDate!);
    if (expiry == null) return null;
    final diff = expiry.difference(DateTime.now()).inDays;
    return diff < 0 ? 0 : diff;
  }
}
