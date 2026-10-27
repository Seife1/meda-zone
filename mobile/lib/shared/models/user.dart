class AppUser {
  final String id;
  final String phoneNumber;
  final String? displayName;
  final String? profilePhotoUrl;
  final List<String> preferredPositions;
  final String role; // PLAYER | FIELD_OWNER | SUPER_ADMIN
  final bool isActive;

  const AppUser({
    required this.id,
    required this.phoneNumber,
    this.displayName,
    this.profilePhotoUrl,
    required this.preferredPositions,
    required this.role,
    required this.isActive,
  });

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
        id: j['id'] as String,
        phoneNumber: j['phone_number'] as String,
        displayName: j['display_name'] as String?,
        profilePhotoUrl: j['profile_photo_url'] as String?,
        preferredPositions:
            (j['preferred_positions'] as List<dynamic>? ?? [])
                .map((e) => e as String)
                .toList(),
        role: j['role'] as String? ?? 'PLAYER',
        isActive: j['is_active'] as bool? ?? true,
      );

  AppUser copyWith({
    String? id,
    String? phoneNumber,
    String? displayName,
    String? profilePhotoUrl,
    List<String>? preferredPositions,
    String? role,
    bool? isActive,
  }) =>
      AppUser(
        id: id ?? this.id,
        phoneNumber: phoneNumber ?? this.phoneNumber,
        displayName: displayName ?? this.displayName,
        profilePhotoUrl: profilePhotoUrl ?? this.profilePhotoUrl,
        preferredPositions: preferredPositions ?? this.preferredPositions,
        role: role ?? this.role,
        isActive: isActive ?? this.isActive,
      );
}
