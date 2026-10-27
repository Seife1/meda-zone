import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import '../../core/api_client.dart';
import '../../core/constants.dart';
import '../../core/local_db.dart';
import '../../core/location_service.dart';
import '../../shared/models/field.dart';

/// Stream of connectivity status — true = online.
final networkStatusProvider = StreamProvider<bool>((ref) {
  return Connectivity()
      .onConnectivityChanged
      .map((result) => result != ConnectivityResult.none);
});

/// One-shot GPS position.
final locationProvider = FutureProvider<LatLng?>((ref) async {
  final result = await UserLocationService.ensureAccess();
  if (!result.granted) return null;
  return UserLocationService.getCurrentPosition();
});

/// Filter state model.
class FieldFilter {
  final String? surfaceType;
  final String? amenities;
  final double? minPrice;
  final double? maxPrice;
  final String? availableDate;
  final String? q;

  const FieldFilter({
    this.surfaceType,
    this.amenities,
    this.minPrice,
    this.maxPrice,
    this.availableDate,
    this.q,
  });

  FieldFilter copyWith({
    String? surfaceType,
    String? amenities,
    double? minPrice,
    double? maxPrice,
    String? availableDate,
    String? q,
    bool clearSurfaceType = false,
    bool clearAmenities = false,
    bool clearQ = false,
  }) =>
      FieldFilter(
        surfaceType: clearSurfaceType ? null : (surfaceType ?? this.surfaceType),
        amenities: clearAmenities ? null : (amenities ?? this.amenities),
        minPrice: minPrice ?? this.minPrice,
        maxPrice: maxPrice ?? this.maxPrice,
        availableDate: availableDate ?? this.availableDate,
        q: clearQ ? null : (q ?? this.q),
      );
}

final filterProvider = StateProvider<FieldFilter>((ref) => const FieldFilter());

/// Nearby fields — fetches from API or falls back to local cache.
class NearbyFieldsNotifier extends StateNotifier<AsyncValue<List<Field>>> {
  NearbyFieldsNotifier() : super(const AsyncLoading());

  Future<void> fetch({
    double? lat,
    double? lng,
    FieldFilter filter = const FieldFilter(),
  }) async {
    state = const AsyncLoading();
    try {
      final params = <String, dynamic>{
        'radius_km': AppConstants.searchRadiusKm,
        if (lat != null) 'lat': lat,
        if (lng != null) 'lng': lng,
        if (filter.surfaceType != null) 'surface_type': filter.surfaceType,
        if (filter.amenities != null) 'amenities': filter.amenities,
        if (filter.minPrice != null) 'min_price': filter.minPrice,
        if (filter.maxPrice != null) 'max_price': filter.maxPrice,
        if (filter.availableDate != null) 'available_date': filter.availableDate,
        if (filter.q != null) 'q': filter.q,
      };

      final resp = await ApiClient.dio.get('/fields', queryParameters: params);
      final rawList = resp.data as List<dynamic>;
      final fields = rawList
          .map((j) => Field.fromJson(j as Map<String, dynamic>))
          .toList();

      // Cache for offline use
      await localDb.upsertFields(
          rawList.cast<Map<String, dynamic>>());

      state = AsyncData(fields);
    } catch (_) {
      // Fallback to cache
      final cached = await localDb.getFields();
      if (cached.isNotEmpty) {
        state = AsyncData(cached.map((j) => Field.fromJson(j)).toList());
      } else {
        state = AsyncError(_, StackTrace.current);
      }
    }
  }
}

final nearbyFieldsProvider =
    StateNotifierProvider<NearbyFieldsNotifier, AsyncValue<List<Field>>>(
  (ref) => NearbyFieldsNotifier(),
);
