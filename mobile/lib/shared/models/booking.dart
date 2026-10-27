class Booking {
  final String id;
  final String reference;
  final String playerId;
  final String fieldId;
  final String slotId;
  final String? subscriptionId;
  final String slotDate;
  final String slotStartTime;
  final String slotEndTime;
  final String status; // confirmed | checked_in | cancelled
  final String? cancellationReason;
  final String? cancelledAt;
  final String? checkedInAt;
  final String createdAt;

  const Booking({
    required this.id,
    required this.reference,
    required this.playerId,
    required this.fieldId,
    required this.slotId,
    this.subscriptionId,
    required this.slotDate,
    required this.slotStartTime,
    required this.slotEndTime,
    required this.status,
    this.cancellationReason,
    this.cancelledAt,
    this.checkedInAt,
    required this.createdAt,
  });

  factory Booking.fromJson(Map<String, dynamic> j) => Booking(
        id: j['id'] as String,
        reference: j['reference'] as String,
        playerId: j['player_id'] as String,
        fieldId: j['field_id'] as String,
        slotId: j['slot_id'] as String,
        subscriptionId: j['subscription_id'] as String?,
        slotDate: j['slot_date'] as String,
        slotStartTime: j['slot_start_time'] as String,
        slotEndTime: j['slot_end_time'] as String,
        status: j['status'] as String? ?? 'confirmed',
        cancellationReason: j['cancellation_reason'] as String?,
        cancelledAt: j['cancelled_at'] as String?,
        checkedInAt: j['checked_in_at'] as String?,
        createdAt: j['created_at'] as String,
      );
}
