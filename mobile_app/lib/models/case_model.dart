class CasePhoto {
  final int id;
  final String photoPath;
  final bool isPrimary;
  final String? uploadedAt;

  CasePhoto({
    required this.id,
    required this.photoPath,
    required this.isPrimary,
    this.uploadedAt,
  });

  factory CasePhoto.fromJson(Map<String, dynamic> json) {
    return CasePhoto(
      id: json['id'] ?? 0,
      photoPath: json['photo_path'] ?? '',
      isPrimary: json['is_primary'] == true || json['is_primary'] == 1,
      uploadedAt: json['uploaded_at'],
    );
  }
}

class CaseModel {
  final int id;
  final String referenceNo;
  final String fullName;
  final int age;
  final String gender;
  final String lastSeenDate;
  final String lastSeenLocation;
  final double? lastSeenLat;
  final double? lastSeenLng;
  final String status;
  final String? clothingDescription;
  final String? medicalConditions;
  final List<CasePhoto> photos;

  CaseModel({
    required this.id,
    required this.referenceNo,
    required this.fullName,
    required this.age,
    required this.gender,
    required this.lastSeenDate,
    required this.lastSeenLocation,
    this.lastSeenLat,
    this.lastSeenLng,
    required this.status,
    this.clothingDescription,
    this.medicalConditions,
    required this.photos,
  });

  factory CaseModel.fromJson(Map<String, dynamic> json) {
    var rawPhotos = json['photos'] as List? ?? [];
    List<CasePhoto> photoList = rawPhotos.map((p) => CasePhoto.fromJson(p)).toList();

    return CaseModel(
      id: json['id'] ?? 0,
      referenceNo: json['reference_no'] ?? '',
      fullName: json['full_name'] ?? 'Unknown Individual',
      age: json['age'] ?? 0,
      gender: json['gender'] ?? 'Unspecified',
      lastSeenDate: json['last_seen_date'] ?? '',
      lastSeenLocation: json['last_seen_location'] ?? 'Unknown',
      lastSeenLat: (json['last_seen_lat'] as num?)?.toDouble(),
      lastSeenLng: (json['last_seen_lng'] as num?)?.toDouble(),
      status: json['status'] ?? 'active',
      clothingDescription: json['clothing_description'],
      medicalConditions: json['medical_conditions'],
      photos: photoList,
    );
  }

  String get primaryPhotoUrl {
    final primary = photos.firstWhere(
      (p) => p.isPrimary,
      orElse: () => photos.isNotEmpty ? photos.first : CasePhoto(id: 0, photoPath: '', isPrimary: false),
    );
    return primary.photoPath;
  }
}
