class SightingReceiptModel {
  final String receiptNumber;
  final String status;
  final String submittedAt;
  final String locationName;
  final double? latitude;
  final double? longitude;
  final String notes;

  SightingReceiptModel({
    required this.receiptNumber,
    required this.status,
    required this.submittedAt,
    required this.locationName,
    this.latitude,
    this.longitude,
    required this.notes,
  });

  factory SightingReceiptModel.fromJson(Map<String, dynamic> json) {
    return SightingReceiptModel(
      receiptNumber: json['receipt_number'] ?? json['receipt'] ?? '',
      status: json['status'] ?? 'received',
      submittedAt: json['submitted_at'] ?? json['created_at'] ?? DateTime.now().toIso8601String(),
      locationName: json['location_name'] ?? 'Unknown location',
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
      notes: json['notes'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'receipt_number': receiptNumber,
      'status': status,
      'submitted_at': submittedAt,
      'location_name': locationName,
      'latitude': latitude,
      'longitude': longitude,
      'notes': notes,
    };
  }
}
