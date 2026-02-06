-- MediTrack Database Schema for Supabase PostgreSQL

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create custom types
CREATE TYPE user_role AS ENUM ('patient', 'caregiver', 'doctor');
CREATE TYPE reminder_status AS ENUM ('pending', 'taken', 'missed', 'skipped');
CREATE TYPE risk_level AS ENUM ('minor', 'moderate', 'major');

-- Users table (extends Supabase auth.users)
CREATE TABLE public.users (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    phone TEXT,
    date_of_birth DATE,
    role user_role DEFAULT 'patient',
    is_family_admin BOOLEAN DEFAULT FALSE,
    emergency_contact TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Family groups
CREATE TABLE public.family_groups (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    admin_user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Family members (linking users to family groups)
CREATE TABLE public.family_members (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    family_group_id UUID REFERENCES public.family_groups(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    relationship TEXT, -- 'self', 'parent', 'child', 'spouse', etc.
    can_manage BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(family_group_id, user_id)
);

-- Medical conditions
CREATE TABLE public.conditions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    severity risk_level DEFAULT 'minor',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User medical history
CREATE TABLE public.medical_histories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    condition_id UUID REFERENCES public.conditions(id) ON DELETE CASCADE,
    diagnosed_date DATE,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, condition_id)
);

-- Allergies
CREATE TABLE public.allergies (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    allergen TEXT NOT NULL,
    reaction TEXT,
    severity risk_level DEFAULT 'moderate',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Medications lookup table
CREATE TABLE public.medications (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    generic_name TEXT,
    brand_names TEXT[], -- Array of brand names
    drug_class TEXT,
    description TEXT,
    common_dosages TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- OCR uploads and prescription parsing
CREATE TABLE public.ocr_uploads (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    original_image_url TEXT,
    raw_ocr_text TEXT,
    confidence_score DECIMAL(3,2),
    source_type TEXT, -- 'printed', 'handwritten', 'mixed'
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Extracted medicines from OCR
CREATE TABLE public.extracted_medicines (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    ocr_upload_id UUID REFERENCES public.ocr_uploads(id) ON DELETE CASCADE,
    medication_id UUID REFERENCES public.medications(id),
    extracted_name TEXT NOT NULL,
    dosage TEXT,
    frequency TEXT,
    duration TEXT,
    confidence_score DECIMAL(3,2),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Prescription sources (doctors, hospitals, etc.)
CREATE TABLE public.prescription_sources (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    ocr_upload_id UUID REFERENCES public.ocr_uploads(id) ON DELETE CASCADE,
    doctor_name TEXT,
    hospital_clinic TEXT,
    license_number TEXT,
    contact_info JSONB,
    prescription_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Drug interactions database (from TWOSIDES)
CREATE TABLE public.drug_interactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    drug1_name TEXT NOT NULL,
    drug2_name TEXT NOT NULL,
    interaction_type TEXT,
    severity risk_level,
    description TEXT,
    frequency_score DECIMAL(10,6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(drug1_name, drug2_name)
);

-- Drug interaction checking logs
CREATE TABLE public.interaction_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    medications_checked TEXT[],
    interactions_found JSONB,
    risk_summary TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Drug lookup cache
CREATE TABLE public.drug_lookup_cache (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    drug_combination_hash TEXT UNIQUE NOT NULL,
    medications TEXT[],
    interaction_results JSONB,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- AI explanations from Gemini
CREATE TABLE public.ai_explanations (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    medication_list TEXT[],
    risk_factors JSONB,
    explanation TEXT,
    explanation_format TEXT DEFAULT 'markdown', -- 'markdown', 'json', 'plain'
    prompt_used TEXT,
    tokens_used INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- QR code tokens for encrypted sharing
CREATE TABLE public.qr_tokens (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    encrypted_data TEXT NOT NULL,
    encryption_method TEXT DEFAULT 'AES-256',
    expires_at TIMESTAMP WITH TIME ZONE,
    max_uses INTEGER DEFAULT 1,
    current_uses INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- QR access logs
CREATE TABLE public.qr_access_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    qr_token_id UUID REFERENCES public.qr_tokens(id) ON DELETE CASCADE,
    accessed_by_ip TEXT,
    accessed_by_user_agent TEXT,
    access_location JSONB, -- Geographic info if available
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Medication schedules and reminders
CREATE TABLE public.medication_schedules (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    medication_id UUID REFERENCES public.medications(id),
    medication_name TEXT NOT NULL,
    dosage TEXT,
    frequency_per_day INTEGER,
    times_of_day TIME[],
    start_date DATE DEFAULT CURRENT_DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Reminder logs and tracking
CREATE TABLE public.reminder_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    schedule_id UUID REFERENCES public.medication_schedules(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP WITH TIME ZONE,
    actual_time TIMESTAMP WITH TIME ZONE,
    status reminder_status DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Export logs for doctor dashboard
CREATE TABLE public.export_logs (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    export_type TEXT, -- 'json', 'pdf', 'csv'
    exported_data JSONB,
    exported_by_user_id UUID REFERENCES public.users(id),
    export_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.family_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.family_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medical_histories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.allergies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ocr_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.extracted_medicines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interaction_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_explanations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.qr_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.qr_access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medication_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reminder_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.export_logs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "Users can view own data" ON public.users
    FOR ALL USING (auth.uid() = id);

-- Family group policies
CREATE POLICY "Family members can view group data" ON public.family_groups
    FOR SELECT USING (
        auth.uid() IN (
            SELECT user_id FROM public.family_members 
            WHERE family_group_id = id
        )
    );

CREATE POLICY "Family admins can manage groups" ON public.family_groups
    FOR ALL USING (auth.uid() = admin_user_id);

-- Medical data policies
CREATE POLICY "Users can manage own medical data" ON public.medical_histories
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Family caregivers can view member medical data" ON public.medical_histories
    FOR SELECT USING (
        auth.uid() = user_id OR 
        auth.uid() IN (
            SELECT fm.user_id FROM public.family_members fm
            JOIN public.family_members target_fm ON fm.family_group_id = target_fm.family_group_id
            WHERE target_fm.user_id = medical_histories.user_id 
            AND fm.can_manage = true
        )
    );

-- Similar policies for other sensitive tables...
CREATE POLICY "Users can manage own allergies" ON public.allergies
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own OCR uploads" ON public.ocr_uploads
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own AI explanations" ON public.ai_explanations
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own QR tokens" ON public.qr_tokens
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own medication schedules" ON public.medication_schedules
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own extracted medicines" ON public.extracted_medicines
FOR ALL USING (
    auth.uid() IN (
        SELECT user_id FROM public.ocr_uploads 
        WHERE id = extracted_medicines.ocr_upload_id
    )
);

-- Family member policies
CREATE POLICY "Users can manage family members" ON public.family_members
    FOR ALL USING (
        auth.uid() = user_id OR 
        auth.uid() IN (
            SELECT admin_user_id FROM public.family_groups 
            WHERE id = family_members.family_group_id
        )
    );

-- Interaction logs policies
CREATE POLICY "Users can manage own interaction logs" ON public.interaction_logs
    FOR ALL USING (auth.uid() = user_id);

-- QR access logs policies
CREATE POLICY "Users can view QR access logs" ON public.qr_access_logs
    FOR SELECT USING (
        auth.uid() IN (
            SELECT user_id FROM public.qr_tokens 
            WHERE id = qr_access_logs.qr_token_id
        )
    );

-- Reminder logs policies
CREATE POLICY "Users can manage reminder logs" ON public.reminder_logs
    FOR ALL USING (
        auth.uid() IN (
            SELECT user_id FROM public.medication_schedules 
            WHERE id = reminder_logs.schedule_id
        )
    );

-- Export logs policies
CREATE POLICY "Users can manage own export logs" ON public.export_logs
    FOR ALL USING (auth.uid() = user_id);

-- Indexes for performance
CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_family_members_user_id ON public.family_members(user_id);
CREATE INDEX idx_family_members_group_id ON public.family_members(family_group_id);
CREATE INDEX idx_medical_histories_user_id ON public.medical_histories(user_id);
CREATE INDEX idx_allergies_user_id ON public.allergies(user_id);
CREATE INDEX idx_ocr_uploads_user_id ON public.ocr_uploads(user_id);
CREATE INDEX idx_drug_interactions_drugs ON public.drug_interactions(drug1_name, drug2_name);
CREATE INDEX idx_drug_lookup_cache_hash ON public.drug_lookup_cache(drug_combination_hash);
CREATE INDEX idx_medication_schedules_user_id ON public.medication_schedules(user_id);
CREATE INDEX idx_reminder_logs_schedule_id ON public.reminder_logs(schedule_id);
CREATE INDEX idx_qr_tokens_token ON public.qr_tokens(token);

-- Functions for automated updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_medical_histories_updated_at BEFORE UPDATE ON public.medical_histories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_allergies_updated_at BEFORE UPDATE ON public.allergies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_medication_schedules_updated_at BEFORE UPDATE ON public.medication_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some common medical conditions
INSERT INTO public.conditions (name, description, severity) VALUES
    ('Hypertension', 'High blood pressure', 'moderate'),
    ('Diabetes Type 2', 'Adult-onset diabetes', 'major'),
    ('Diabetes Type 1', 'Insulin-dependent diabetes', 'major'),
    ('Asthma', 'Respiratory condition', 'moderate'),
    ('Heart Disease', 'Cardiovascular conditions', 'major'),
    ('Kidney Disease', 'Chronic kidney disease', 'major'),
    ('Liver Disease', 'Chronic liver conditions', 'major'),
    ('Depression', 'Mental health condition', 'moderate'),
    ('Anxiety', 'Anxiety disorders', 'moderate'),
    ('Arthritis', 'Joint inflammation', 'minor');

-- Insert common medications
INSERT INTO public.medications (name, generic_name, brand_names, drug_class) VALUES
    ('Aspirin', 'acetylsalicylic acid', ARRAY['Bayer', 'Bufferin'], 'NSAID'),
    ('Ibuprofen', 'ibuprofen', ARRAY['Advil', 'Motrin'], 'NSAID'),
    ('Acetaminophen', 'acetaminophen', ARRAY['Tylenol'], 'Analgesic'),
    ('Metformin', 'metformin', ARRAY['Glucophage'], 'Antidiabetic'),
    ('Lisinopril', 'lisinopril', ARRAY['Prinivil', 'Zestril'], 'ACE Inhibitor'),
    ('Amlodipine', 'amlodipine', ARRAY['Norvasc'], 'Calcium Channel Blocker'),
    ('Simvastatin', 'simvastatin', ARRAY['Zocor'], 'Statin'),
    ('Omeprazole', 'omeprazole', ARRAY['Prilosec'], 'Proton Pump Inhibitor');

-- Prescriptions (records of prescriptions issued to users)
CREATE TABLE public.prescriptions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    ocr_upload_id UUID REFERENCES public.ocr_uploads(id),
    doctor_name TEXT,
    clinic_name TEXT,
    prescription_date DATE,
    disease_name TEXT, -- added field to record diagnosis/disease for uniqueness per prescription
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on prescriptions and allow users to manage their own prescriptions
ALTER TABLE public.prescriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own prescriptions" ON public.prescriptions
    FOR ALL USING (auth.uid() = user_id);

CREATE INDEX idx_prescriptions_user_id ON public.prescriptions(user_id);

-- Trigger to update updated_at for prescriptions
CREATE TRIGGER update_prescriptions_updated_at BEFORE UPDATE ON public.prescriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Prescription items (searchable history / user-saved meds)
CREATE TABLE public.prescription_items (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    medication_id UUID REFERENCES public.medications(id),
    medication_name TEXT NOT NULL,
    prescription_id UUID REFERENCES public.prescriptions(id),
    dosage TEXT,
    frequency TEXT,
    duration TEXT,
    start_date DATE,
    end_date DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    -- uniqueness is enforced via indexes (see migrations) so we don't declare a table-level UNIQUE constraint here
);

-- Enable RLS on prescription_items and allow users to manage their own items
ALTER TABLE public.prescription_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own prescription items" ON public.prescription_items
    FOR ALL USING (auth.uid() = user_id);

CREATE INDEX idx_prescription_items_user_id ON public.prescription_items(user_id);

-- Unique constraints for prescription_items:
-- 1. Within a prescription, each medication can only appear once
CREATE UNIQUE INDEX uq_prescription_items_pres_med 
ON public.prescription_items(prescription_id, medication_name) 
WHERE prescription_id IS NOT NULL;

-- 2. For orphan medications (not linked to any prescription), each user can only have one instance of each medication
CREATE UNIQUE INDEX uq_prescription_items_orphan_user_med
ON public.prescription_items(user_id, medication_name) 
WHERE prescription_id IS NULL;
