import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import '../config/theme_tokens.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../models/match_result_model.dart';
import '../widgets/tactical_button.dart';
import '../widgets/status_badge.dart';
import '../widgets/tactical_card.dart';

class ScannerScreen extends StatefulWidget {
  const ScannerScreen({super.key});

  @override
  State<ScannerScreen> createState() => _ScannerScreenState();
}

class _ScannerScreenState extends State<ScannerScreen> {
  final ImagePicker _picker = ImagePicker();
  Uint8List? _selectedImageBytes;
  String? _selectedFileName;
  bool _isAnalyzing = false;
  MatchResponse? _matchResponse;
  String? _errorMessage;

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? file = await _picker.pickImage(
        source: source,
        maxWidth: 1280,
        maxHeight: 1280,
        imageQuality: 85,
      );

      if (file != null) {
        final bytes = await file.readAsBytes();
        setState(() {
          _selectedImageBytes = bytes;
          _selectedFileName = file.name;
          _matchResponse = null;
          _errorMessage = null;
        });
        _runBiometricScan(bytes, file.name);
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to capture photo: $e';
      });
    }
  }

  Future<void> _runBiometricScan(Uint8List bytes, String filename) async {
    setState(() {
      _isAnalyzing = true;
      _errorMessage = null;
    });

    try {
      final result = await ApiService().matchProbePhoto(bytes, filename);
      setState(() {
        _matchResponse = result;
        _isAnalyzing = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceAll('Exception: ', '');
        _isAnalyzing = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.canvas,
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'BIOMETRIC FIELD SCANNER',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: 0.5,
              ),
            ),
            Text(
              'YuNet DNN • SFace MobileFaceNet • L2 Vector Match',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                color: AppColors.primaryHover,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: () {
              setState(() {
                _selectedImageBytes = null;
                _selectedFileName = null;
                _matchResponse = null;
                _errorMessage = null;
              });
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Viewfinder / Probe Preview Container
            Container(
              height: 260,
              decoration: BoxDecoration(
                color: AppColors.card,
                borderRadius: BorderRadius.circular(AppRadius.lg),
                border: Border.all(
                  color: _isAnalyzing ? AppColors.primary : AppColors.border,
                  width: 1.5,
                ),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(AppRadius.lg),
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    if (_selectedImageBytes != null)
                      Image.memory(
                        _selectedImageBytes!,
                        fit: BoxFit.cover,
                      )
                    else
                      Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: AppColors.cardElevated,
                                border: Border.all(color: AppColors.border),
                              ),
                              child: const Icon(
                                Icons.face_retouching_natural,
                                size: 40,
                                color: AppColors.textSecondary,
                              ),
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'Optical Target Viewfinder',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Capture or select subject image to compare with gallery',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 12,
                                color: AppColors.textMuted,
                              ),
                              textAlign: TextAlign.center,
                            ),
                          ],
                        ),
                      ),

                    // Tactical HUD Reticle Overlay
                    IgnorePointer(
                      child: Container(
                        margin: const EdgeInsets.all(24),
                        decoration: BoxDecoration(
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.15),
                            width: 1.0,
                          ),
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                    ),

                    if (_isAnalyzing)
                      Container(
                        color: Colors.black54,
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const CircularProgressIndicator(
                                strokeWidth: 2.5,
                                valueColor: AlwaysStoppedAnimation<Color>(AppColors.primaryHover),
                              ),
                              const SizedBox(height: 14),
                              Text(
                                'EXTRACTING 128-D BIOMETRIC EMBEDDING...',
                                style: GoogleFonts.jetBrainsMono(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: AppSpacing.md),

            // Capture Controls
            Row(
              children: [
                Expanded(
                  child: TacticalButton(
                    label: 'Take Photo',
                    icon: Icons.camera_alt,
                    onPressed: _isAnalyzing ? null : () => _pickImage(ImageSource.camera),
                    variant: TacticalButtonVariant.primary,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: TacticalButton(
                    label: 'From Gallery',
                    icon: Icons.photo_library,
                    onPressed: _isAnalyzing ? null : () => _pickImage(ImageSource.gallery),
                    variant: TacticalButtonVariant.secondary,
                  ),
                ),
              ],
            ),

            if (_selectedFileName != null) ...[
              const SizedBox(height: 6),
              Text(
                'Source: $_selectedFileName',
                style: GoogleFonts.jetBrainsMono(fontSize: 10, color: AppColors.textMuted),
                textAlign: TextAlign.center,
              ),
            ],

            if (_errorMessage != null) ...[
              const SizedBox(height: AppSpacing.md),
              TacticalCard(
                backgroundColor: AppColors.crimsonBg.withValues(alpha: 0.2),
                borderColor: AppColors.crimson.withValues(alpha: 0.5),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline, color: AppColors.crimson, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _errorMessage!,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 13,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Match Results Display
            if (_matchResponse != null) ...[
              const SizedBox(height: AppSpacing.lg),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'GALLERY SEARCH CANDIDATES',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  Text(
                    '${_matchResponse!.matches.length} RANKED',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.primaryHover,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.sm),

              if (_matchResponse!.matches.isEmpty)
                TacticalCard(
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 24),
                      child: Column(
                        children: [
                          const Icon(Icons.search_off, size: 36, color: AppColors.textMuted),
                          const SizedBox(height: 8),
                          Text(
                            'No Gallery Candidates Exceeded Cutoff (≥ 0.50)',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
              else
                ..._matchResponse!.matches.map((candidate) => _buildCandidateCard(candidate)),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildCandidateCard(MatchCandidate candidate) {
    BadgeStyle badgeStyle = BadgeStyle.neutral;
    if (candidate.isHighConfidence) {
      badgeStyle = BadgeStyle.highMatch;
    } else if (candidate.isModerateConfidence) {
      badgeStyle = BadgeStyle.moderate;
    }

    String photoUrl = candidate.referencePhotoUrl ?? '';
    if (photoUrl.isNotEmpty && !photoUrl.startsWith('http')) {
      photoUrl = '${ApiConfig.baseUrl.replaceAll('/api/v1', '')}/$photoUrl';
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: TacticalCard(
        borderColor: candidate.isHighConfidence ? AppColors.emerald.withValues(alpha: 0.5) : AppColors.border,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Enrolled Reference Portrait
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                  child: Container(
                    width: 56,
                    height: 56,
                    color: AppColors.cardElevated,
                    child: photoUrl.isNotEmpty
                        ? Image.network(
                            photoUrl,
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) =>
                                const Icon(Icons.person, color: AppColors.textMuted),
                          )
                        : const Icon(Icons.person, color: AppColors.textMuted),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),

                // Demographics & Match Score
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            candidate.referenceNo,
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: AppColors.textMuted,
                            ),
                          ),
                          StatusBadge(
                            label: '${candidate.confidenceTier} • ${candidate.percentageString}',
                            style: badgeStyle,
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        candidate.fullName,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      if (candidate.euclideanDistance != null)
                        Text(
                          'Euclidean Dist: ${candidate.euclideanDistance!.toStringAsFixed(3)}',
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 10,
                            color: AppColors.textMuted,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
