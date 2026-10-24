import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme_tokens.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../models/case_model.dart';
import '../widgets/status_badge.dart';
import '../widgets/tactical_card.dart';

class CaseDetailScreen extends StatefulWidget {
  final int caseId;
  const CaseDetailScreen({super.key, required this.caseId});

  @override
  State<CaseDetailScreen> createState() => _CaseDetailScreenState();
}

class _CaseDetailScreenState extends State<CaseDetailScreen> {
  CaseModel? _case;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _fetchDetail();
  }

  Future<void> _fetchDetail() async {
    try {
      final detail = await ApiService().getCaseDetail(widget.caseId);
      setState(() {
        _case = detail;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceAll('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.canvas,
      appBar: AppBar(
        title: Text(
          _case != null ? _case!.referenceNo : 'CASE DOSSIER',
          style: GoogleFonts.jetBrainsMono(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(AppColors.primaryHover),
              ),
            )
          : _errorMessage != null
              ? Center(child: Text(_errorMessage!, style: const TextStyle(color: AppColors.crimson)))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(AppSpacing.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Portrait Hero Card
                      Container(
                        height: 280,
                        decoration: BoxDecoration(
                          color: AppColors.card,
                          borderRadius: BorderRadius.circular(AppRadius.lg),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(AppRadius.lg),
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              _buildHeroImage(),
                              // Overlay Gradient
                              Container(
                                decoration: BoxDecoration(
                                  gradient: LinearGradient(
                                    begin: Alignment.topCenter,
                                    end: Alignment.bottomCenter,
                                    colors: [
                                      Colors.transparent,
                                      Colors.black.withValues(alpha: 0.8),
                                    ],
                                  ),
                                ),
                              ),
                              Positioned(
                                bottom: 16,
                                left: 16,
                                right: 16,
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        StatusBadge(
                                          label: _case!.status,
                                          style: BadgeStyle.activeCase,
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          _case!.referenceNo,
                                          style: GoogleFonts.jetBrainsMono(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w700,
                                            color: AppColors.primaryHover,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      _case!.fullName,
                                      style: GoogleFonts.plusJakartaSans(
                                        fontSize: 20,
                                        fontWeight: FontWeight.w700,
                                        color: Colors.white,
                                      ),
                                    ),
                                    Text(
                                      'Age: ${_case!.age} • Gender: ${_case!.gender}',
                                      style: GoogleFonts.plusJakartaSans(
                                        fontSize: 13,
                                        color: AppColors.textSecondary,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: AppSpacing.md),

                      // Demographics & Last Seen Dossier
                      TacticalCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'INCIDENT & DISAPPEARANCE TIMELINE',
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: AppColors.textSecondary,
                                letterSpacing: 0.5,
                              ),
                            ),
                            const SizedBox(height: 12),
                            _buildMetaRow(Icons.calendar_today, 'Last Seen Date', _case!.lastSeenDate),
                            const Divider(color: AppColors.border, height: 16),
                            _buildMetaRow(Icons.place_outlined, 'Last Seen Location', _case!.lastSeenLocation),
                            if (_case!.lastSeenLat != null && _case!.lastSeenLng != null) ...[
                              const Divider(color: AppColors.border, height: 16),
                              _buildMetaRow(
                                Icons.my_location,
                                'GPS Coordinates',
                                '${_case!.lastSeenLat!.toStringAsFixed(4)}° N, ${_case!.lastSeenLng!.toStringAsFixed(4)}° E',
                              ),
                            ],
                          ],
                        ),
                      ),

                      const SizedBox(height: AppSpacing.md),

                      // Forensic Attributes
                      TacticalCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'IDENTIFYING CHARACTERISTICS',
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: AppColors.textSecondary,
                                letterSpacing: 0.5,
                              ),
                            ),
                            const SizedBox(height: 12),
                            _buildMetaRow(
                              Icons.checkroom_outlined,
                              'Clothing Description',
                              _case!.clothingDescription ?? 'None recorded at intake',
                            ),
                            const Divider(color: AppColors.border, height: 16),
                            _buildMetaRow(
                              Icons.medical_services_outlined,
                              'Medical & Special Needs',
                              _case!.medicalConditions ?? 'No recorded medical vulnerability',
                            ),
                          ],
                        ),
                      ),

                      const SizedBox(height: AppSpacing.md),

                      // Emergency Hotline Card
                      TacticalCard(
                        backgroundColor: AppColors.cardElevated,
                        borderColor: AppColors.borderFocus,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                const Icon(Icons.shield_outlined, color: AppColors.primaryHover, size: 20),
                                const SizedBox(width: 8),
                                Text(
                                  'LAW ENFORCEMENT ESCALATION',
                                  style: GoogleFonts.jetBrainsMono(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.primaryHover,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Emergency Hotline: 112 / 100\nInvestigative Helpdesk: missing-help@tnpolice.gov.in',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 12,
                                color: AppColors.textSecondary,
                                height: 1.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildHeroImage() {
    String photoUrl = _case!.primaryPhotoUrl;
    if (photoUrl.isNotEmpty && !photoUrl.startsWith('http')) {
      photoUrl = '${ApiConfig.baseUrl.replaceAll('/api/v1', '')}/$photoUrl';
    }

    if (photoUrl.isEmpty) {
      return const Center(child: Icon(Icons.person, size: 80, color: AppColors.textMuted));
    }

    return Image.network(
      photoUrl,
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) => const Center(
        child: Icon(Icons.person, size: 80, color: AppColors.textMuted),
      ),
    );
  }

  Widget _buildMetaRow(IconData icon, String title, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: AppColors.textMuted),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textMuted,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                value,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
