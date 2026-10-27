import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';
import '../../core/constants.dart';
import '../../core/theme.dart';
import '../../shared/models/field.dart';
import 'map_provider.dart';
import '../field/field_summary_card.dart';

class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> {
  final MapController _mapController = MapController();
  final _searchCtrl = TextEditingController();
  bool _locationDenied = false;

  @override
  void initState() {
    super.initState();
    _loadFields();
  }

  Future<void> _loadFields() async {
    final location = await ref.read(locationProvider.future);
    if (location == null) {
      setState(() => _locationDenied = true);
    }
    await ref.read(nearbyFieldsProvider.notifier).fetch(
          lat: location?.latitude,
          lng: location?.longitude,
        );
    if (location != null && mounted) {
      _mapController.move(location, AppConstants.defaultZoom);
    }
  }

  void _onPinTap(Field field) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => FieldSummaryCard(field: field),
    );
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final fieldsAsync = ref.watch(nearbyFieldsProvider);
    final networkAsync = ref.watch(networkStatusProvider);
    final isOffline = networkAsync.valueOrNull == false;

    return Scaffold(
      appBar: BrandAppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.tune),
            onPressed: () => _showFilterSheet(),
            tooltip: 'Filter fields',
          ),
        ],
      ),
      body: Column(
        children: [
          if (isOffline) const OfflineBanner(),
          if (_locationDenied)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              child: TextField(
                controller: _searchCtrl,
                decoration: InputDecoration(
                  hintText: 'Search by neighborhood or landmark…',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: () {
                      ref.read(nearbyFieldsProvider.notifier).fetch(
                            filter: FieldFilter(q: _searchCtrl.text.trim()),
                          );
                    },
                  ),
                ),
                onSubmitted: (q) => ref
                    .read(nearbyFieldsProvider.notifier)
                    .fetch(filter: FieldFilter(q: q.trim())),
              ),
            ),
          Expanded(
            child: fieldsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.error_outline, size: 48, color: AppColors.error),
                    const SizedBox(height: 12),
                    Text('Could not load fields', style: Theme.of(context).textTheme.bodyLarge),
                    const SizedBox(height: 8),
                    ElevatedButton(onPressed: _loadFields, child: const Text('Retry')),
                  ],
                ),
              ),
              data: (fields) => FlutterMap(
                mapController: _mapController,
                options: MapOptions(
                  initialCenter: LatLng(AppConstants.defaultLat, AppConstants.defaultLng),
                  initialZoom: AppConstants.defaultZoom,
                ),
                children: [
                  TileLayer(
                    urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                    userAgentPackageName: 'et.medazone.app',
                  ),
                  MarkerLayer(
                    markers: fields.map((field) {
                      final isSponsored = field.isSponsored;
                      return Marker(
                        point: LatLng(field.lat, field.lng),
                        width: 44,
                        height: 44,
                        child: GestureDetector(
                          onTap: () => _onPinTap(field),
                          child: Container(
                            decoration: BoxDecoration(
                              color: isSponsored
                                  ? const Color(0xFFFFD700) // gold for sponsored
                                  : AppColors.primaryGreen, // green for standard
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.2),
                                  blurRadius: 4,
                                ),
                              ],
                            ),
                            child: const Icon(Icons.sports_soccer, color: Colors.white, size: 22),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showFilterSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => _FilterSheet(
        onApply: (filter) {
          Navigator.pop(ctx);
          ref.read(nearbyFieldsProvider.notifier).fetch(filter: filter);
        },
      ),
    );
  }
}

class _FilterSheet extends StatefulWidget {
  final void Function(FieldFilter) onApply;
  const _FilterSheet({required this.onApply});

  @override
  State<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<_FilterSheet> {
  String? _surfaceType;
  RangeValues _priceRange = const RangeValues(0, 2000);
  bool _priceFilterEnabled = false;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, MediaQuery.of(context).viewInsets.bottom + 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Handle
          Center(
            child: Container(
              width: 40, height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Text('Filter Fields', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 16),

          // Surface type
          Text('Surface Type', style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: ['grass', 'artificial', 'futsal'].map((t) {
              return ChoiceChip(
                label: Text(t[0].toUpperCase() + t.substring(1)),
                selected: _surfaceType == t,
                onSelected: (_) => setState(() => _surfaceType = _surfaceType == t ? null : t),
                selectedColor: AppColors.primaryGreen.withOpacity(0.2),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),

          // Price range — Fix #8
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Price Range', style: Theme.of(context).textTheme.titleSmall),
              Switch(
                value: _priceFilterEnabled,
                onChanged: (v) => setState(() => _priceFilterEnabled = v),
                activeColor: AppColors.primaryGreen,
              ),
            ],
          ),
          if (_priceFilterEnabled) ...[
            RangeSlider(
              values: _priceRange,
              min: 0,
              max: 2000,
              divisions: 40,
              activeColor: AppColors.primaryGreen,
              inactiveColor: AppColors.primaryGreen.withOpacity(0.2),
              labels: RangeLabels(
                'ETB ${_priceRange.start.toInt()}',
                'ETB ${_priceRange.end.toInt()}',
              ),
              onChanged: (values) => setState(() => _priceRange = values),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('ETB ${_priceRange.start.toInt()}/hr',
                    style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
                Text('ETB ${_priceRange.end.toInt()}/hr',
                    style: const TextStyle(fontSize: 12, color: AppColors.textMuted)),
              ],
            ),
          ],

          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: () => widget.onApply(FieldFilter(
              surfaceType: _surfaceType,
              minPrice: _priceFilterEnabled ? _priceRange.start : null,
              maxPrice: _priceFilterEnabled ? _priceRange.end : null,
            )),
            child: const Text('Apply Filters'),
          ),
          TextButton(
            onPressed: () {
              setState(() {
                _surfaceType = null;
                _priceRange = const RangeValues(0, 2000);
                _priceFilterEnabled = false;
              });
              widget.onApply(const FieldFilter());
            },
            child: const Text('Clear All'),
          ),
        ],
      ),
    );
  }
}

