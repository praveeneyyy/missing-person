class UserModel {
  final int id;
  final String username;
  final String email;
  final String fullName;
  final String badgeNumber;
  final String role;
  final String? token;

  UserModel({
    required this.id,
    required this.username,
    required this.email,
    required this.fullName,
    required this.badgeNumber,
    required this.role,
    this.token,
  });

  factory UserModel.fromJson(Map<String, dynamic> json, {String? token}) {
    return UserModel(
      id: json['id'] ?? 0,
      username: json['username'] ?? '',
      email: json['email'] ?? '',
      fullName: json['full_name'] ?? '',
      badgeNumber: json['badge_number'] ?? 'N/A',
      role: json['role'] ?? 'public',
      token: token,
    );
  }

  bool get isInvestigator => role == 'investigator' || role == 'admin';
  bool get isAdmin => role == 'admin';
}
