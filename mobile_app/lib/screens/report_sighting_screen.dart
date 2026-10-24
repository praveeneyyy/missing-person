import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/theme_tokens.dart';
import '../services/api_service.dart';
import '../widgets/tactical_button.dart';
import '../widgets/tactical_card.dart';

class ReportSightingScreen extends StatefulWidget {
  const ReportSightingScreen({super.key});

  @override
  State<ReportSightingScreen> createState() => _ReportSightingScreenState();
}

class _ReportSightingScreenState extends State<ReportSightingScreen> {
  final ImagePicker _picker = ImagePicker();
  Uint8List? _imageBytes;
  String? _fileName;

  final TextEditingController _locationController = TextEditingController(text: 'Central Bus Terminal, Chennai');
  final TextEditingController _latController = TextEditingController(text: '13.0827');
  final TextEditingController _lngController = TextEditingController(text: '80.2707');
  final TextEditingController _notesController = TextEditingController();

  bool _isSubmitting = false;
  String? _submittedReceipt;
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
          _imageBytes = bytes;
          _fileName = file.name;
          _errorMessage = null;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to capture image: $e';
      });
    }
  }

  Future<void> _submitReport() async {
    if (_imageBytes == null) {
      setState(() {
        _errorMessage = 'Please take or select a sighting photograph first.';
      });
      return;
    }

    if (_locationController.text.trim().isEmpty) {
      setState(() {
        _errorMessage = 'Please provide a location name or description.';
      });
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final double? lat = double.tryParse(_latController.text.trim());
      final double? lng = double.tryParse(_lngController.text.trim());

      final receipt = await ApiService().submitSighting(
        imageBytes: _imageBytes!,
        filename: _fileName ?? 'sighting.jpg',
        locationName: _locationController.text.trim(),
        latitude: lat,
        longitude: lng,
        notes: _notesController.text.trim(),
      );

      // Save receipt to local wallet
      final prefs = await SharedPreferences.getInstance();
      List<String> savedReceipts = prefs.getStringList('saved_receipts') ?? [];
      final receiptData = jsonEncode({
        'receipt_number': receipt,
        'location_name': _locationController.text.trim(),
        'submitted_at': DateTime.now().toIso8601String(),
        'status': 'received',
      });
      savedReceipts.insert(0, receiptData);
      await prefs.setStringList('saved_receipts', savedReceipts);

      setState(() {
        _submittedReceipt = receipt;
        _isSubmitting = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceAll('Exception: ', '');
        _isSubmitting = false;
      });
    }
  }

  void _resetForm() {
    setState(() {
      _imageBytes = null;
      _fileName = null;
      _submittedReceipt = null;
      _notesController.clear();
      _errorMessage = null;
    });
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
              'REPORT A SIGHTING',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: 0.5,
              ),
            ),
            Text(
              'Tamper-Resistant Public & Field Intake Portal',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: _submittedReceipt != null ? _buildReceiptSuccessCard() : _buildIntakeForm(),
      ),
    );
  }

  Widget _buildIntakeForm() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Photo Capture Card
        Container(
          height: 200,
          decoration: BoxDecoration(
            color: AppColors.card,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(color: AppColors.border),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: _imageBytes != null
                ? Image.memory(_imageBytes!, fit: BoxFit.cover)
                : Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.add_a_photo_outlined, size: 36, color: AppColors.textMuted),
                        const SizedBox(height: 8),
                        Text(
                          'Sighting Evidence Photo',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Upload photo of individual or surveillance frame',
                          style: GoogleFonts.plusJakartaSans(fontSize: 12, color: AppColors.textMuted),
                        ),
                      ],
                    ),
                  ),
          ),
        ),

        const SizedBox(height: AppSpacing.sm),

        // Photo Action Buttons
        Row(
          children: [
            Expanded(
              child: TacticalButton(
                label: 'Use Camera',
                icon: Icons.camera_alt,
                onPressed: () => _pickImage(ImageSource.camera),
                variant: TacticalButtonVariant.secondary,
                height: 42,
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: TacticalButton(
                label: 'Choose Photo',
                icon: Icons.photo_library,
                onPressed: () => _pickImage(ImageSource.gallery),
                variant: TacticalButtonVariant.secondary,
                height: 42,
              ),
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.md),

        // Location & GPS Information
        TacticalCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'LOCATION & GEODETIC METADATA',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textSecondary,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _locationController,
                style: GoogleFonts.plusJakartaSans(fontSize: 13, color: AppColors.textPrimary),
                decoration: const InputDecoration(
                  labelText: 'Location Name / Landmark',
                  prefixIcon: Icon(Icons.place_outlined, size: 18, color: AppColors.textMuted),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _latController,
                      style: GoogleFonts.jetBrainsMono(fontSize: 12, color: AppColors.textPrimary),
                      decoration: const InputDecoration(
                        labelText: 'Latitude',
                        prefixIcon: Icon(Icons.my_location, size: 16, color: AppColors.textMuted),
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: TextField(
                      controller: _lngController,
                      style: GoogleFonts.jetBrainsMono(fontSize: 12, color: AppColors.textPrimary),
                      decoration: const InputDecoration(
                        labelText: 'Longitude',
                        prefixIcon: Icon(Icons.navigation_outlined, size: 16, color: AppColors.textMuted),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        const SizedBox(height: AppSpacing.md),

        // Observation Notes
        TacticalCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'OBSERVATION NOTES (OPTIONAL)',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textSecondary,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _notesController,
                maxLines: 3,
                style: GoogleFonts.plusJakartaSans(fontSize: 13, color: AppColors.textPrimary),
                decoration: const InputDecoration(
                  hintText: 'Observed clothing, companion details, behavior, or directional heading...',
                ),
              ),
            ],
          ),
        ),

        if (_errorMessage != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(
            _errorMessage!,
            style: const TextStyle(color: AppColors.crimson, fontSize: 13),
            textAlign: TextAlign.center,
          ),
        ],

        const SizedBox(height: AppSpacing.lg),

        // Submit Button
        TacticalButton(
          label: 'Submit Official Sighting',
          icon: Icons.send_rounded,
          onPressed: _isSubmitting ? null : _submitReport,
          isLoading: _isSubmitting,
          variant: TacticalButtonVariant.primary,
          height: 52,
        ),
      ],
    );
  }

  Widget _buildReceiptSuccessCard() {
    return TacticalCard(
      backgroundColor: AppColors.cardElevated,
      borderColor: AppColors.emerald.withValues(alpha: 0.5),
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.emeraldBg.withValues(alpha: 0.4),
              border: Border.all(color: AppColors.emerald),
            ),
            child: const Icon(Icons.check_circle_outline, size: 48, color: AppColors.emerald),
          ),
          const SizedBox(height: 16),
          Text(
            'Sighting Successfully Recorded',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Your submission has been queued for automated biometric extraction and investigator verification.',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 13,
              color: AppColors.textSecondary,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),

          // Receipt Identifier Box
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppColors.canvas,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              children: [
                Text(
                  'CONFIDENTIAL TRACKING RECEIPT',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textMuted,
                  ),
                ),
                const SizedBox(height: 4),
                SelectableText(
                  _submittedReceipt!,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: AppColors.primaryHover,
                    letterSpacing: 1.0,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          TacticalButton(
            label: 'Submit Another Sighting',
            icon: Icons.add,
            onPressed: _resetForm,
            variant: TacticalButtonVariant.secondary,
          ),
        ],
      ),
    );
  }
}
