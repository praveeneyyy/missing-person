class MatchCandidate {
  final int caseId;
  final String referenceNo;
  final String fullName;
  final double similarityScore;
  final String confidenceTier;
  final String? referencePhotoUrl;
  final double? euclideanDistance;

  MatchCandidate({
    required this.caseId,
    required this.referenceNo,
    required this.fullName,
    required this.similarityScore,
    required this.confidenceTier,
    this.referencePhotoUrl,
    this.euclideanDistance,
  });

  factory MatchCandidate.fromJson(Map<String, dynamic> json) {
    return MatchCandidate(
      caseId: json['case_id'] ?? 0,
      referenceNo: json['reference_no'] ?? 'N/A',
      fullName: json['full_name'] ?? 'Unknown Candidate',
      similarityScore: (json['similarity_score'] as num?)?.toDouble() ?? 0.0,
      confidenceTier: json['confidence_tier'] ?? 'Low',
      referencePhotoUrl: json['reference_photo_url'] ?? json['photo_url'],
      euclideanDistance: (json['euclidean_distance'] as num?)?.toDouble(),
    );
  }

  bool get isHighConfidence => similarityScore >= 0.70 || confidenceTier.toLowerCase() == 'high';
  bool get isModerateConfidence => similarityScore >= 0.50 && similarityScore < 0.70;
  String get percentageString => '${(similarityScore * 100).toStringAsFixed(1)}%';
}

class MatchResponse {
  final bool success;
  final int totalGalleryFaces;
  final int probeFacesDetected;
  final List<MatchCandidate> matches;
  final String? message;

  MatchResponse({
    required this.success,
    required this.totalGalleryFaces,
    required this.probeFacesDetected,
    required this.matches,
    this.message,
  });

  factory MatchResponse.fromJson(Map<String, dynamic> json) {
    var rawMatches = json['matches'] as List? ?? [];
    return MatchResponse(
      success: json['success'] ?? true,
      totalGalleryFaces: json['total_gallery_faces'] ?? 0,
      probeFacesDetected: json['probe_faces_detected'] ?? 1,
      matches: rawMatches.map((m) => MatchCandidate.fromJson(m)).toList(),
      message: json['message'],
    );
  }
}
