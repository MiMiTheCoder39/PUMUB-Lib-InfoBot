-- ============================================================
-- DEV / TEST SEED DATA ONLY — DO NOT RUN IN PRODUCTION
-- ============================================================
-- These records exist ONLY for local development and automated
-- testing of the Phase H verification layer. They are NOT real
-- university identities. Fabricated identities are never used in
-- production; in production this table is populated exclusively
-- from the registrar's official enrollment data.
--
-- To wipe this dev data: DELETE FROM university_records;
-- (no production data exists in this table at this time)
-- ============================================================

INSERT INTO university_records
  (university_email, university_id, full_name, faculty_id, department, year, role, is_active)
VALUES
  -- STUDENT record (Faculty of Computing / Information Science)
  ('devtest.student@pumub.edu.mm', 'MUB-9001', 'Dev Test Student', 7, 'Information Science (IS)', '2', 'student', 1),

  -- TEACHER record (Faculty of Computing / Computer Science)
  ('devtest.teacher@pumub.edu.mm', 'T-099', 'Dev Test Teacher', 1, 'Computer Science (CS)', NULL, 'teacher', 1),

  -- INACTIVE record (deliberately ineligible — must be rejected)
  ('devtest.inactive@pumub.edu.mm', 'MUB-9002', 'Dev Test Inactive', 3, 'Civil', '1', 'student', 0),

  -- STUDENT record with no faculty/department/year (faculty_id NULL)
  ('devtest.plain@pumub.edu.mm', 'MUB-9003', 'Dev Plain Student', NULL, NULL, NULL, 'student', 1),

  -- STUDENT record reserved for the tamper/forgery test case
  ('devtest.two@pumub.edu.mm', 'MUB-9004', 'Dev Test Two', 1, 'Computer Science (CS)', '1', 'student', 1),

  -- ============================================================
  -- DEV records for the regression test suites (phaseB / phaseC /
  -- phaseG). TEST DATA ONLY — never load in production.
  -- ============================================================

  -- phaseB suite identities (fixed, see phaseB_test.py)
  ('phb.test2299@pumub.edu.mm', 'MUB-2299', 'Phb Test Student', 7, 'Information Science (IS)', '2', 'student', 1),
  ('phb.t2281@pumub.edu.mm', 'T-2281', 'Phb Test Teacher', 1, 'Computer Science (CS)', NULL, 'teacher', 1),
  ('phb.cs9910@pumub.edu.mm', 'CS-2025-010', 'Phb Cs Student', 1, 'Computer Science (CS)', '1', 'student', 1),
  ('phb.dup7701@pumub.edu.mm', 'MUB-7701', 'Phb Dup Student', 1, 'Computer Science (CS)', '1', 'student', 1),
  ('phb.lock9922@pumub.edu.mm', 'MUB-9922', 'Phb Lock Student', 1, 'Computer Science (CS)', '1', 'student', 1),

  -- phaseC suite identities (deterministic, see phaseC_test.py)
  ('phasec.s1@pumub.edu.mm', 'MUB-8101', 'Phasec Student One', 7, 'Information Science (IS)', '1', 'student', 1),
  ('phasec.s2@pumub.edu.mm', 'MUB-8102', 'Phasec Student Two', 1, 'Computer Science (CS)', '2', 'student', 1),
  ('phasec.s3@pumub.edu.mm', 'MUB-8103', 'Phasec Student Three', 1, 'Computer Science (CS)', '3', 'student', 1),
  ('phasec.t1@pumub.edu.mm', 'T-8101', 'Phasec Teacher One', 1, 'Computer Science (CS)', NULL, 'teacher', 1),

  -- phaseG suite identities (deterministic, see phaseG_test.py)
  ('phg.new@pumub.edu.mm', 'MUB-8001', 'Phg New Student', 7, 'Information Science (IS)', '1', 'student', 1),
  ('phg.tam@pumub.edu.mm', 'MUB-8002', 'Phg Tamper Student', 1, 'Computer Science (CS)', '1', 'student', 1);
