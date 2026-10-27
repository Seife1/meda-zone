import 'slot.dart';

class Field {
  final String id;
  final String name;
  final String address;
  final String? neighborhood;
  final double lat;
  final double lng;
  final String surfaceType; // grass | artificial | futsal
  final String? fieldSize;
  final Map<String, dynamic> amenities;
  final double pricePerHour;
  final Map<String, dynamic> operatingHours;
  final List<String> photoUrls;
  final double averageRating;
  final int reviewCount;
  final bool isActive;
  final bool isSponsored;
  final double? distanceKm;
  final Slot? nextAvailableSlot;

  const Field({
    required this.id,
    required this.name,
    required this.address,
    this.neighborhood,
    required this.lat,
    required this.lng,
    required this.surfaceType,
    this.fieldSize,
    required this.amenities,
    required this.pricePerHour,
    required this.operatingHours,
    required this.photoUrls,
    required this.averageRating,
    required this.reviewCount,
    required this.isActive,
    required this.isSponsored,
    this.distanceKm,
    this.nextAvailableSlot,
  });

  static double _toDouble(dynamic v) {
    if (v == null) return 0.0;
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v) ?? 0.0;
    return 0.0;
  }

  factory Field.fromJson(Map<String, dynamic> j) => Field(
        id: j['id'] as String,
        name: j['name'] as String,
        address: j['address'] as String,
        neighborhood: j['neighborhood'] as String?,
        lat: _toDouble(j['lat']),
        lng: _toDouble(j['lng']),
        surfaceType: j['surface_type'] as String? ?? 'grass',
        fieldSize: j['field_size'] as String?,
        amenities:
            (j['amenities'] as Map<String, dynamic>?) ?? const {},
        pricePerHour: _toDouble(j['price_per_hour']),
        operatingHours:
            (j['operating_hours'] as Map<String, dynamic>?) ?? const {},
        photoUrls: (j['photo_urls'] as List<dynamic>? ?? [])
            .map((e) => e as String)
            .toList(),
        averageRating: _toDouble(j['average_rating']),
        reviewCount: j['review_count'] as int? ?? 0,
        isActive: j['is_active'] as bool? ?? true,
        isSponsored: j['is_sponsored'] as bool? ?? false,
        distanceKm: j['distance_km'] != null ? _toDouble(j['distance_km']) : null,
        nextAvailableSlot: j['next_available_slot'] == null
            ? null
            : Slot.fromJson(
                j['next_available_slot'] as Map<String, dynamic>),
      );
}
