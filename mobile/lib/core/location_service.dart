import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Result of checking / requesting location permission and device GPS.
class LocationAccessResult {
  final bool granted;
  final bool servicesEnabled;

  const LocationAccessResult({
    required this.granted,
    required this.servicesEnabled,
  });
}

/// Foreground GPS helpers used by the map screen.
class UserLocationService {
  UserLocationService._();

  /// Minimum movement (meters) before emitting another stream update.
  static const int distanceFilterMeters = 3;

  /// Re-fetch nearby stations when the user moves farther than this (km).
  static const double stationsRefreshDistanceKm = 0.2;

  static const _distance = Distance();

  static LocationSettings get _settings => const LocationSettings(
        accuracy: LocationAccuracy.best,
        distanceFilter: distanceFilterMeters,
      );

  static Future<LocationAccessResult> ensureAccess() async {
    final servicesEnabled = await Geolocator.isLocationServiceEnabled();
    if (!servicesEnabled) {
      return const LocationAccessResult(
        granted: false,
        servicesEnabled: false,
      );
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    final granted = permission == LocationPermission.always ||
        permission == LocationPermission.whileInUse;

    return LocationAccessResult(
      granted: granted,
      servicesEnabled: true,
    );
  }

  /// Live GPS updates while the map screen is open.
  static Stream<LatLng> positionStream() {
    return Geolocator.getPositionStream(locationSettings: _settings).map(
      (pos) => LatLng(pos.latitude, pos.longitude),
    );
  }

  /// One-shot high-accuracy fix (e.g. when the user taps "my location").
  static Future<LatLng?> getCurrentPosition() async {
    final access = await ensureAccess();
    if (!access.granted) return null;
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.best,
        timeLimit: const Duration(seconds: 8),
      );
      return LatLng(pos.latitude, pos.longitude);
    } catch (_) {
      return null;
    }
  }

  static bool shouldRefreshStations(LatLng? anchor, LatLng current) {
    if (anchor == null) return true;
    return _distance.as(
          LengthUnit.Kilometer,
          anchor,
          current,
        ) >=
        stationsRefreshDistanceKm;
  }

  static Future<void> openLocationSettings() =>
      Geolocator.openLocationSettings();

  static Future<void> openAppSettings() => Geolocator.openAppSettings();
}
