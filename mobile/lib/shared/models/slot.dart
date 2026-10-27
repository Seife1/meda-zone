class Slot {
  final String id;
  final String fieldId;
  final String slotDate;    // "2025-07-14"
  final String startTime;   // "16:00"
  final String endTime;     // "17:00"
  final int durationMinutes;
  final String status; // available | pending | booked | closed

  const Slot({
    required this.id,
    required this.fieldId,
    required this.slotDate,
    required this.startTime,
    required this.endTime,
    required this.durationMinutes,
    required this.status,
  });

  factory Slot.fromJson(Map<String, dynamic> j) => Slot(
        id: j['id'] as String,
        fieldId: j['field_id'] as String,
        slotDate: j['slot_date'] as String,
        startTime: j['start_time'] as String,
        endTime: j['end_time'] as String,
        durationMinutes: j['duration_minutes'] as int? ?? 60,
        status: j['status'] as String? ?? 'available',
      );
}
