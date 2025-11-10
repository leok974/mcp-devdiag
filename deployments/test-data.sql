-- Insert test diagnostic runs
INSERT INTO devdiag.diag_run (ts, tenant, target_hash, env_fp, problems, evidence, preset)
VALUES
  (now() - interval '7 days', 'tasteos', 'hash1', 'env_fp1', '["CSP_INLINE_BLOCKED", "XFO_DENY"]'::jsonb, '{"framework": "react@18.3.1", "xfo": "DENY"}'::jsonb, 'chat'),
  (now() - interval '6 days', 'tasteos', 'hash1', 'env_fp1', '["CSP_INLINE_BLOCKED"]'::jsonb, '{"framework": "react@18.3.1", "xfo": "SAMEORIGIN"}'::jsonb, 'chat'),
  (now() - interval '5 days', 'tasteos', 'hash1', 'env_fp1', '[]'::jsonb, '{"framework": "react@18.3.1", "xfo": "SAMEORIGIN"}'::jsonb, 'chat'),
  (now() - interval '2 days', 'tasteos', 'hash2', 'env_fp2', '["FRAMEWORK_OUTDATED"]'::jsonb, '{"framework": "vue@2.6.0"}'::jsonb, 'app'),
  (now() - interval '1 day', 'tasteos', 'hash2', 'env_fp2', '["FRAMEWORK_OUTDATED"]'::jsonb, '{"framework": "vue@2.6.0"}'::jsonb, 'app');

-- Insert test fix outcomes
INSERT INTO devdiag.fix_outcome (ts, tenant, problem_code, fix_code, confidence, support, env_fp, notes)
VALUES
  (now() - interval '6 days', 'tasteos', 'XFO_DENY', 'FIX_XFO_SAMEORIGIN', 0.95, 1, 'env_fp1', 'Auto-labeled success'),
  (now() - interval '5 days', 'tasteos', 'CSP_INLINE_BLOCKED', 'FIX_CSP_NONCE', 0.85, 1, 'env_fp1', 'Auto-labeled success')
ON CONFLICT (tenant, problem_code, fix_code, env_fp) DO UPDATE
  SET support = devdiag.fix_outcome.support + EXCLUDED.support,
      confidence = EXCLUDED.confidence;

SELECT 'Test data inserted successfully' AS status;
