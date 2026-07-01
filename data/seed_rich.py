"""
Seed 50 realistic, varied citizen submissions across all 10 issue themes,
8 Indian languages, and geo-spread across Andhra Pradesh / Telangana.
Run: python data/seed_rich.py
"""
import random, time, requests

BASE = "https://citizens-india-backend-564262191703.us-central1.run.app"

# Narasaraopet area coordinates ± spread
def coords():
    return round(16.22 + random.uniform(-0.4, 0.4), 4), round(80.12 + random.uniform(-0.4, 0.4), 4)

SUBMISSIONS = [
    # Roads & Infrastructure
    ("Roads & Infrastructure", "en", "The road from Pedanandipadu to taluk hospital is completely broken for 3 km. Ambulances cannot pass and two patients died last month. Over 400 families are affected.", "Demo Constituency"),
    ("Roads & Infrastructure", "hi", "हमारे गाँव की सड़क बहुत खराब है। बरसात में बच्चे स्कूल नहीं जा पाते। 6 महीने से कोई मरम्मत नहीं हुई। 250 परिवार प्रभावित हैं।", "Demo Constituency"),
    ("Roads & Infrastructure", "te", "మా గ్రామం నుండి మండల కేంద్రానికి వెళ్ళే రోడ్డు పాడైపోయింది. వర్షాకాలంలో రోడ్డు మీద నడవడం కూడా కష్టంగా ఉంది. 300 కుటుంబాలు ఇబ్బంది పడుతున్నాయి.", "Demo Constituency"),
    ("Roads & Infrastructure", "en", "Bridge over Nagarjuna canal near Vinukonda collapsed partially 2 months ago. School buses are taking a 15 km detour. Urgently needs repair.", "Demo Constituency"),
    ("Roads & Infrastructure", "ta", "எங்கள் தெருவில் சாலை முழுவதும் குழிகள் நிறைந்துள்ளன. இரு சக்கர வாகனங்கள் விழுந்து 3 பேர் காயமடைந்தனர். உடனடியாக சரிசெய்ய வேண்டும்.", "Demo Constituency"),
    ("Roads & Infrastructure", "en", "Street lights on main road from Chilakaluripet to Sattenapalli are non-functional for 8 months. Night accidents have increased. Women feel unsafe walking after 7 PM.", "Demo Constituency"),
    ("Roads & Infrastructure", "hi", "पीडब्ल्यूडी सड़क पर बड़े-बड़े गड्ढे हैं। दो पहिया वाहन चालकों के लिए बेहद खतरनाक। पिछले महीने 5 दुर्घटनाएं हुईं।", "Demo Constituency"),
    ("Roads & Infrastructure", "en", "Drainage overflows onto the main road during every rain, making it impassable. The drainage system was built in 1986 and never upgraded.", "Demo Constituency"),

    # Water Supply
    ("Water Supply", "te", "మా కాలనీలో నల్లా నీళ్ళు వారానికి ఒకసారి మాత్రమే వస్తున్నాయి. గత 3 నెలలుగా నీటి సమస్య తీవ్రంగా ఉంది. 500 కుటుంబాలు ప్రభావితమవుతున్నాయి.", "Demo Constituency"),
    ("Water Supply", "en", "Borewell installed last year is now giving contaminated water with high fluoride. Children in our village have dental and bone problems. 120 households affected.", "Demo Constituency"),
    ("Water Supply", "hi", "हमारे गाँव में पानी की टंकी 6 महीने पहले टूट गई। अभी तक मरम्मत नहीं हुई। महिलाएं 3 किलोमीटर दूर से पानी लाती हैं।", "Demo Constituency"),
    ("Water Supply", "en", "Water pipeline is leaking at 4 points on the main road. Wasting thousands of litres daily. Road also getting damaged due to waterlogging.", "Demo Constituency"),
    ("Water Supply", "kn", "ನಮ್ಮ ಊರಿನಲ್ಲಿ ಕೊಳವೆ ನೀರು ವಾರದಲ್ಲಿ ಎರಡು ಬಾರಿ ಮಾತ್ರ ಬರುತ್ತದೆ. ಬೇಸಿಗೆಯಲ್ಲಿ ಪರಿಸ್ಥಿತಿ ಇನ್ನೂ ಕಷ್ಟಕರ.", "Demo Constituency"),
    ("Water Supply", "en", "Open canal water is being used for drinking in Thullur mandal because taps run dry. Risk of cholera outbreak. Children are falling sick frequently.", "Demo Constituency"),

    # Healthcare & Sanitation
    ("Healthcare & Sanitation", "en", "Primary Health Centre in our mandal has no doctor since 6 months. Only an ANM is present. Pregnant women have to travel 25 km to district hospital.", "Demo Constituency"),
    ("Healthcare & Sanitation", "ta", "எங்கள் ஊர் அரசு மருத்துவமனையில் மருந்துகள் இல்லை. நோயாளிகள் தனியார் மருத்துவமனைக்கு செல்ல வேண்டியுள்ளது. ஏழை மக்களுக்கு மிகவும் கஷ்டமாக உள்ளது.", "Demo Constituency"),
    ("Healthcare & Sanitation", "en", "Open defecation in our panchayat because 60% of households have no toilets. Swachh Bharat funds were sanctioned but work not started. Rainy season diseases are spreading.", "Demo Constituency"),
    ("Healthcare & Sanitation", "hi", "हमारे क्षेत्र में डेंगू के 20 से ज़्यादा मामले आए हैं। नालियों में पानी जमा है, मच्छर पनप रहे हैं। फॉगिंग के लिए कई बार आवेदन किया लेकिन कोई नहीं आया।", "Demo Constituency"),
    ("Healthcare & Sanitation", "en", "Garbage collected only once a week in our ward. Waste is piling up near the school. Children are falling ill due to stench and flies. Need daily collection.", "Demo Constituency"),

    # Education
    ("Education", "en", "Government school has 380 students but only 4 teachers. Classes 6, 7, 8 have no subject teachers — one teacher takes all subjects. Quality of learning is very poor.", "Demo Constituency"),
    ("Education", "te", "మా గ్రామ పాఠశాలలో భవనం శిథిలావస్థలో ఉంది. వర్షాకాలంలో పిల్లలు తడుస్తూ చదువుతున్నారు. కొత్త భవనం కట్టించాలని విజ్ఞప్తి.", "Demo Constituency"),
    ("Education", "hi", "मिड-डे मील में बच्चों को हर दिन वही खाना मिलता है — चावल और दाल। अंडे और फल का आवंटन आता है लेकिन बच्चों तक नहीं पहुँचता।", "Demo Constituency"),
    ("Education", "en", "School has no functioning toilets for girls. This is the main reason girl students in classes 6-8 are dropping out. Toilet block needs urgent repair.", "Demo Constituency"),
    ("Education", "en", "No computer lab or internet in government school despite Digital India promises. 200 students in 9th and 10th cannot access online learning materials.", "Demo Constituency"),

    # Electricity
    ("Electricity", "en", "Power cuts of 8-10 hours daily during summer. Agricultural borewells cannot run. Crops are dying. Scheduled cuts are not followed — unscheduled outages are constant.", "Demo Constituency"),
    ("Electricity", "te", "మా గ్రామంలో రాత్రిపూట కరెంటు లేదు. సోలార్ స్ట్రీట్ లైట్లు పాడయ్యాయి. దొంగల భయంతో రాత్రిపూట ఎవరూ బయటకు రావడం లేదు.", "Demo Constituency"),
    ("Electricity", "en", "Transformer serving 3 villages has been faulty for 2 months. APEPDCL keeps promising replacement but nothing has happened. 800 households affected.", "Demo Constituency"),
    ("Electricity", "en", "High electricity bills despite low usage. When we complained to DISCOM office, they refused to check the meter. We suspect meter is defective.", "Demo Constituency"),

    # Agriculture & Irrigation
    ("Agriculture & Irrigation", "en", "Canal sluice gates are broken and farmers cannot get water for rabi crops. The gates were supposed to be repaired under irrigation budget last year. 200 acres affected.", "Demo Constituency"),
    ("Agriculture & Irrigation", "hi", "किसान क्रेडिट कार्ड के लिए 4 बार बैंक गए लेकिन अधिकारी हर बार नए कागज़ात माँग रहे हैं। छोटे किसान साहूकारों से कर्ज़ ले रहे हैं।", "Demo Constituency"),
    ("Agriculture & Irrigation", "te", "పంట నష్టపరిహారం 2 సంవత్సరాల నుండి రాలేదు. సైక్లోన్‌లో నష్టపోయిన రైతులు ఇంకా నష్టపరిహారం కోసం వేచి చూస్తున్నారు.", "Demo Constituency"),
    ("Agriculture & Irrigation", "en", "Cold storage facility promised 3 years ago never built. Farmers lose 30% of their tomato and onion produce due to lack of storage. Urgently needed.", "Demo Constituency"),

    # Housing & Land
    ("Housing & Land", "en", "PMAY housing list was prepared 2 years ago but houses not constructed. Beneficiaries received first installment but contractor abandoned work after foundation.", "Demo Constituency"),
    ("Housing & Land", "hi", "हमारी ज़मीन का पट्टा नहीं मिला। 15 साल से उसी ज़मीन पर रह रहे हैं लेकिन सरकारी रिकॉर्ड में नाम नहीं है। बच्चों की पढ़ाई और राशन कार्ड में दिक्कत हो रही है।", "Demo Constituency"),
    ("Housing & Land", "en", "Flood-affected families given temporary shelters in 2022 are still living there. Promised permanent houses not yet built. 35 families stuck in leaking tin sheds.", "Demo Constituency"),

    # Employment & Livelihood
    ("Employment & Livelihood", "en", "MGNREGS work in our panchayat has stopped for 3 months. Job cards are active but no work orders issued. Labourers are going to cities for daily wage work.", "Demo Constituency"),
    ("Employment & Livelihood", "te", "స్వయం సహాయ సంఘాలకు నిధులు రావడం లేదు. మహిళలు చేసిన ఉత్పత్తులకు మార్కెట్ లేదు. ప్రభుత్వ సహాయం కావాలి.", "Demo Constituency"),
    ("Employment & Livelihood", "en", "Youth in our area are highly educated but unemployed. Skill development centre building is constructed but never opened. 500 youth waiting for vocational training.", "Demo Constituency"),

    # Law & Order / Public Safety
    ("Law & Order", "en", "No police outpost in our panchayat cluster of 8 villages. Nearest police station is 18 km away. Petty thefts and eve-teasing incidents increasing. Women feel unsafe.", "Demo Constituency"),
    ("Law & Order", "en", "Illegal sand mining happening at night on the Krishna river bank. Riverbed is destabilising. Local complaints to police have been ignored for 6 months.", "Demo Constituency"),

    # Environment & Waste
    ("Environment & Waste", "en", "Illegal factory dumping chemical waste into the local lake. Fish have died. Drinking water from borewells smells of chemicals. Kids have skin rashes.", "Demo Constituency"),
    ("Environment & Waste", "te", "మా ప్రాంతంలో చెట్లు చాలా తక్కువగా ఉన్నాయి. వేసవిలో ఉష్ణోగ్రత చాలా ఎక్కువగా ఉంటోంది. వృక్షారోపణ కార్యక్రమాలు చేపట్టాలని కోరుతున్నాము.", "Demo Constituency"),
    ("Environment & Waste", "en", "Plastic waste burning near residential area every evening. CPCB norms are being violated. Children have respiratory problems. Local body is ignoring complaints.", "Demo Constituency"),
]

LANG_MAP = {"en": "en", "hi": "hi", "te": "te", "ta": "ta", "kn": "kn", "ml": "ml", "mr": "mr", "bn": "bn"}

def seed():
    success = 0
    for i, (theme, lang, text, constituency) in enumerate(SUBMISSIONS):
        lat, lng = coords()
        try:
            r = requests.post(f"{BASE}/submissions/text", json={
                "text": text,
                "language": lang,
                "constituency": constituency,
                "lat": lat,
                "lng": lng,
            }, timeout=30)
            if r.status_code == 200:
                data = r.json()
                success += 1
                print(f"[{i+1:02d}/{len(SUBMISSIONS)}] ✓ {data.get('theme','?')} | {data.get('urgency','?')} | id={str(data.get('id','?'))[:8]}")
            else:
                print(f"[{i+1:02d}] ✗ {r.status_code}: {r.text[:80]}")
        except Exception as e:
            print(f"[{i+1:02d}] ✗ {e}")
        time.sleep(0.6)  # gentle rate limiting

    print(f"\n✅ Seeded {success}/{len(SUBMISSIONS)} submissions")

if __name__ == "__main__":
    seed()
