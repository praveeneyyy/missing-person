import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/theme_tokens.dart';
import '../services/api_service.dart';
import '../models/sighting_receipt_model.dart';
import '../widgets/status_badge.dart';
import '../widgets/tactical_card.dart';
import '../widgets/tactical_button.dart';

class ReceiptWalletScreen extends StatefulWidget {
  const ReceiptWalletScreen({super.key});

  @override
  State<ReceiptWalletScreen> createState() => _ReceiptWalletScreenState();
}

class _ReceiptWalletScreenState extends State<ReceiptWalletScreen> {
  final TextEditingController _receiptInputController = TextEditingController();
  SightingReceiptModel? _lookedUpReceipt;
  bool _isSearching = false;
  String? _searchError;
  List<Map<String, dynamic>> _savedReceipts = [];

  @override
  void initState() {
    super.initState();
    _loadSavedReceipts();
  }

  Future<void> _loadSavedReceipts() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getStringList('saved_receipts') ?? [];
    setState(() {
      _savedReceipts = raw.map((item) => jsonDecode(item) as Map<String, dynamic>).toList();
    });
  }

  Future<void> _searchReceipt(String receiptNo) async {
    final clean = receiptNo.trim().toUpperCase();
    if (clean.isEmpty) return;

    setState(() {
      _isSearching = true;
      _searchError = null;
      _lookedUpReceipt = null;
    });

    try {
      final result = await ApiService().lookupReceipt(clean);
      setState(() {
        _lookedUpReceipt = result;
        _isSearching = false;
      });
    } catch (e) {
      setState(() {
        _searchError = e.toString().replaceAll('Exception: ', '');
        _isSearching = false;
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
              'RECEIPT STATUS TRACKER',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
                letterSpacing: 0.5,
              ),
            ),
            Text(
              'Zero-Knowledge Citizen Inquiry Verification',
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Lookup Search Box
            TacticalCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'INSPECT SUBMISSION RECEIPT',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textSecondary,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _receiptInputController,
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                          decoration: const InputDecoration(
                            hintText: 'e.g. STG-2026-9841',
                            prefixIcon: Icon(Icons.receipt_long, size: 18, color: AppColors.textMuted),
                          ),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      TacticalButton(
                        label: 'Lookup',
                        onPressed: () => _searchReceipt(_receiptInputController.text),
                        isLoading: _isSearching,
                        height: 48,
                      ),
                    ],
                  ),
                ],
              ),
            ),

            if (_searchError != null) ...[
              const SizedBox(height: AppSpacing.md),
              TacticalCard(
                backgroundColor: AppColors.crimsonBg.withValues(alpha: 0.2),
                borderColor: AppColors.crimson.withValues(alpha: 0.5),
                child: Text(
                  _searchError!,
                  style: const TextStyle(color: AppColors.crimson, fontSize: 13),
                  textAlign: TextAlign.center,
                ),
              ),
            ],

            if (_lookedUpReceipt != null) ...[
              const SizedBox(height: AppSpacing.md),
              _buildReceiptCard(_lookedUpReceipt!),
            ],

            const SizedBox(height: AppSpacing.lg),

            // Saved Local Receipts History
            Text(
              'LOCALLY SAVED SUBMISSION RECEIPTS',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: AppColors.textSecondary,
                letterSpacing: 0.5,
              ),
            ),
            const SizedBox(height: AppSpacing.sm),

            if (_savedReceipts.isEmpty)
              TacticalCard(
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 20),
                    child: Column(
                      children: [
                        const Icon(Icons.history_toggle_off, size: 36, color: AppColors.textMuted),
                        const SizedBox(height: 8),
                        Text(
                          'No local sighting receipts recorded on this device yet.',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 12,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              )
            else
              ..._savedReceipts.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                  child: TacticalCard(
                    onTap: () {
                      _receiptInputController.text = item['receipt_number'] ?? '';
                      _searchReceipt(_receiptInputController.text);
                    },
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              item['receipt_number'] ?? 'STG-UNKNOWN',
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                                color: AppColors.primaryHover,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              item['location_name'] ?? 'Recorded Sighting',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 12,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                        StatusBadge(
                          label: item['status'] ?? 'received',
                          style: BadgeStyle.neutral,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildReceiptCard(SightingReceiptModel receipt) {
    BadgeStyle badgeStyle = BadgeStyle.neutral;
    if (receipt.status == 'verified') {
      badgeStyle = BadgeStyle.highMatch;
    } else if (receipt.status == 'under_review') {
      badgeStyle = BadgeStyle.moderate;
    }

    return TacticalCard(
      backgroundColor: AppColors.cardElevated,
      borderColor: AppColors.primary,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                receipt.receiptNumber,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryHover,
                ),
              ),
              StatusBadge(label: receipt.status, style: badgeStyle),
            ],
          ),
          const Divider(color: AppColors.border, height: 20),
          _buildRow('Status Description', _getStatusDescription(receipt.status)),
          const SizedBox(height: 8),
          _buildRow('Reported Location', receipt.locationName),
          const SizedBox(height: 8),
          _buildRow('Intake Timestamp', receipt.submittedAt),
          if (receipt.latitude != null && receipt.longitude != null) ...[
            const SizedBox(height: 8),
            _buildRow('Coordinates', '${receipt.latitude!.toStringAsFixed(4)}°, ${receipt.longitude!.toStringAsFixed(4)}°'),
          ],
        ],
      ),
    );
  }

  String _getStatusDescription(String status) {
    switch (status.toLowerCase()) {
      case 'received':
        return 'Sighting received and queued for biometric feature extraction.';
      case 'under_review':
        return 'Assigned to law enforcement investigators for comparative verification.';
      case 'verified':
        return 'Confirmed by lead investigator. Active response protocols initiated.';
      case 'closed':
        return 'Review completed and archived into evidence records.';
      default:
        return 'Active in system queue.';
    }
  }

  Widget _buildRow(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: GoogleFonts.plusJakartaSans(fontSize: 11, color: AppColors.textMuted),
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 13,
            fontWeight: FontWeight.w500,
            color: AppColors.textPrimary,
          ),
        ),
      ],
    );
  }
}
