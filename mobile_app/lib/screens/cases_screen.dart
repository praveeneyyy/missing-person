import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../config/theme_tokens.dart';
import '../config/api_config.dart';
import '../services/api_service.dart';
import '../models/case_model.dart';
import '../widgets/status_badge.dart';
import '../widgets/tactical_card.dart';
import 'case_detail_screen.dart';

class CasesScreen extends StatefulWidget {
  const CasesScreen({super.key});

  @override
  State<CasesScreen> createState() => _CasesScreenState();
}

class _CasesScreenState extends State<CasesScreen> {
  List<CaseModel> _allCases = [];
  List<CaseModel> _filteredCases = [];
  bool _isLoading = true;
  String? _errorMessage;
  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _fetchCases();
  }

  Future<void> _fetchCases() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final cases = await ApiService().getCases();
      setState(() {
        _allCases = cases;
        _filteredCases = cases;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceAll('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  void _filterCases(String query) {
    final clean = query.trim().toLowerCase();
    setState(() {
      if (clean.isEmpty) {
        _filteredCases = _allCases;
      } else {
        _filteredCases = _allCases.where((c) {
          return c.fullName.toLowerCase().contains(clean) ||
              c.referenceNo.toLowerCase().contains(clean) ||
              c.lastSeenLocation.toLowerCase().contains(clean);
        }).toList();
      }
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
              'MISSING PERSONS REPOSITORY',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: 0.5,
              ),
            ),
            Text(
              'Active National Biometric Watchlist Directory',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: _fetchCases,
          ),
        ],
      ),
      body: Column(
        children: [
          // Tactical Search Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.sm),
            child: TextField(
              controller: _searchController,
              onChanged: _filterCases,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 14,
                color: AppColors.textPrimary,
              ),
              decoration: InputDecoration(
                hintText: 'Search by name, reference (MP-2026-xxx), or city...',
                prefixIcon: const Icon(Icons.search, size: 20, color: AppColors.textMuted),
                suffixIcon: _searchController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear, size: 18),
                        onPressed: () {
                          _searchController.clear();
                          _filterCases('');
                        },
                      )
                    : null,
              ),
            ),
          ),

          // Case List
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(AppColors.primaryHover),
                    ),
                  )
                : _errorMessage != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(AppSpacing.lg),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.cloud_off, size: 40, color: AppColors.crimson),
                              const SizedBox(height: 12),
                              Text(
                                _errorMessage!,
                                textAlign: TextAlign.center,
                                style: GoogleFonts.plusJakartaSans(color: AppColors.textSecondary),
                              ),
                              const SizedBox(height: 16),
                              ElevatedButton(
                                onPressed: _fetchCases,
                                child: const Text('Retry Connection'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _filteredCases.isEmpty
                        ? Center(
                            child: Text(
                              'No matching cases found',
                              style: GoogleFonts.plusJakartaSans(color: AppColors.textMuted),
                            ),
                          )
                        : RefreshIndicator(
                            onRefresh: _fetchCases,
                            color: AppColors.primaryHover,
                            backgroundColor: AppColors.card,
                            child: ListView.builder(
                              padding: const EdgeInsets.all(AppSpacing.md),
                              itemCount: _filteredCases.length,
                              itemBuilder: (context, index) {
                                final item = _filteredCases[index];
                                return _buildCaseCard(item);
                              },
                            ),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildCaseCard(CaseModel item) {
    String photoUrl = item.primaryPhotoUrl;
    if (photoUrl.isNotEmpty && !photoUrl.startsWith('http')) {
      photoUrl = '${ApiConfig.baseUrl.replaceAll('/api/v1', '')}/$photoUrl';
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: TacticalCard(
        onTap: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (_) => CaseDetailScreen(caseId: item.id),
            ),
          );
        },
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Portrait Thumbnail
            ClipRRect(
              borderRadius: BorderRadius.circular(AppRadius.sm),
              child: Container(
                width: 60,
                height: 72,
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

            // Metadata
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        item.referenceNo,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primaryHover,
                        ),
                      ),
                      StatusBadge(
                        label: item.status,
                        style: item.status == 'resolved' ? BadgeStyle.highMatch : BadgeStyle.activeCase,
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    item.fullName,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Age: ${item.age} • ${item.gender}',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.location_on_outlined, size: 14, color: AppColors.textMuted),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          item.lastSeenLocation,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 12,
                            color: AppColors.textMuted,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, size: 20, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}
