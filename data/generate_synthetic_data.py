import json
import random
import os
from datetime import datetime, timedelta

# Constants for Generation
PLATFORMS = ["X", "Instagram", "Facebook", "YouTube"]
CITIES = [
    {"name": "Ahmedabad", "lat": 23.0225, "lon": 72.5714},
    {"name": "Surat", "lat": 21.1702, "lon": 72.8311},
    {"name": "Vadodara", "lat": 22.3072, "lon": 73.1812},
    {"name": "Rajkot", "lat": 22.3039, "lon": 70.8022},
    {"name": "Gandhinagar", "lat": 23.2156, "lon": 72.6369},
    {"name": "Bhavnagar", "lat": 21.7645, "lon": 72.1519},
    {"name": "Jamnagar", "lat": 22.4707, "lon": 70.0577},
    {"name": "Junagadh", "lat": 21.5222, "lon": 70.4579},
    {"name": "Anand", "lat": 22.5645, "lon": 72.9289},
    {"name": "Nadiad", "lat": 22.6948, "lon": 72.8638}
]

USERNAMES_POOL = [
    "amit_patel99", "neha_shah_vlogs", "surat_talks", "ahmedabad_now", "gujju_tiger",
    "modi_bhakt_12", "rajkot_rocker", "drashti_vyas", "rahul_sharma_94", "priya_desai",
    "truth_seeker_in", "kabir_khan_786", "hindustani_warrior", "hardik_patel_fan",
    "bhavnagar_bites", "jamnagar_chatter", "gandhinagar_official", "riddhi_parmar",
    "krunal_mehta", "bhumi_joshi", "parth_travels", "deepa_mishra", "ankit_verma",
    "news_alert_guj", "cyber_sentinel", "desi_chronicle", "vox_populi_guj", "nadiad_news"
]

LANGUAGES = ["english", "hindi", "gujarati", "hinglish", "gujlish"]
CATEGORIES = ["neutral", "inflammatory", "incitement", "fake_news"]

# Templates dictionary structured by [language][category]
TEMPLATES = {
    "english": {
        "neutral": [
            "Had an amazing time walking around Sabarmati Riverfront in {city} today! Weather was beautiful.",
            "Just checked out the new tech park in {city}. Super proud of the development here.",
            "Can anyone recommend the best places to visit in {city} over the weekend?",
            "The explanation in this YouTube tutorial is top notch! Saved me hours of debugging.",
            "Highly recommend checking out the local heritage tour when you are in {city}.",
            "Attended a wonderful cultural fest in {city} last night. The music and food were spectacular.",
            "Does anyone know if the library in {city} is open on Sundays?",
            "Just watched the highlights of the match. What a brilliant comeback by the team!"
        ],
        "inflammatory": [
            "This local politician in {city} is a complete fraud. Anyone who votes for them is brain-dead.",
            "The municipal corporation of {city} is absolute garbage. Lazy officers eating away public money.",
            "I hate how these outsiders are coming to {city} and ruin our beautiful culture. Go back!",
            "Honestly, the fans of this actor are toxic and annoying. Get a life, idiots.",
            "Most news anchors today are just paid sellouts who divide the country for ratings. Shameless trash.",
            "This company's customer support is a joke. I hope they go bankrupt soon.",
            "Typical hypocrites! They talk about equality but display extreme bias in their actions.",
            "These keyboard warriors have no real courage. Cowards venting online."
        ],
        "incitement": [
            "Time to take matters into our own hands. Let's gather at {city} square tomorrow and burn their offices. Bring rods!",
            "If the police won't arrest this criminal, we should block the highway near {city} and smash every car trying to pass.",
            "He deserves to be publically lynched. Let's track down his address in {city} and teach him a lesson he won't survive.",
            "Let's storm the government building in {city} this Friday. We must destroy their records and kick them out.",
            "No more peaceful protests. We must retaliate with violence. Attack their shops tonight!",
            "If they enter our neighborhood in {city}, make sure they don't walk out. Arm yourselves.",
            "Let's vandalize their trucks and disrupt their supply chain. Smash them all!",
            "Track down these traitors and drag them out of their homes. Time for real action.",
            "I will destroy you. Watch your back.",
            "I will kill you. Your time is up.",
            "I will find you and make you pay.",
            "You will pay for this. I will find where you live and hurt you."
        ],
        "fake_news": [
            "BREAKING: Secret government order leaked! A complete internet shutdown across {city} starting tonight. Stock up cash!",
            "ALERT: New scientific research confirms the latest virus strain is deliberately mixed into municipal tap water in {city}.",
            "ALERT: Major chemical leak reported from an industrial unit near {city}. Government is hiding the high death counts!",
            "Leaked files show that a top bank in {city} is filing for bankruptcy. Withdraw all your money immediately!",
            "WARNING: Do not buy salt this week. Artificial plastic salt from China is flooded in {city} markets. Check barcode!",
            "URGENT: NASA satellite report warns of a massive earthquake targeting {city} region in next 48 hours. Evacuate now!",
            "Shocking news: Local authorities are mixing cheap vaccine components. Secret test video goes viral.",
            "Inside report: Major political party is hiring foreign actors to trigger artificial riots in {city} next week."
        ]
    },
    "hindi": {
        "neutral": [
            "आज {city} में साबरमती रिवरफ्रंट पर टहलने का बहुत अच्छा अनुभव रहा। मौसम शानदार था।",
            "अभी {city} में नया डेवलपमेंट प्रोजेक्ट देखा। शहर की प्रगति देखकर बहुत गर्व हुआ।",
            "क्या कोई मुझे {city} में वीकेंड पर घूमने की बेहतरीन जगहें बता सकता है?",
            "इस यूट्यूब वीडियो का एक्सप्लेनेशन बहुत अच्छा है! समझने में बहुत आसानी हुई।",
            "अगर आप {city} में हैं तो यहां की हेरिटेज वॉक का हिस्सा जरूर बनें, अद्भुत अनुभव है।",
            "कल रात {city} के सांस्कृतिक महोत्सव में बहुत मज़ा आया। संगीत और खाना दोनों लाजवाब थे।",
            "क्या किसी को पता है कि {city} में मुख्य लाइब्रेरी रविवार को खुलती है या नहीं?",
            "मैच की हाइलाइट्स देखीं, टीम ने सचमुच शानदार वापसी की है!"
        ],
        "inflammatory": [
            "हमारे {city} का यह नेता बिल्कुल भ्रष्ट और धोखेबाज़ है। ऐसे लोगों को वोट देने वाले महामूर्ख हैं।",
            "{city} का नगर निगम पूरी तरह से बेकार है। कामचोर अधिकारी जनता का पैसा खा रहे हैं।",
            "मुझे गुस्सा आता है कि बाहर के लोग {city} में आकर हमारे शहर की शांति और संस्कृति को बिगाड़ रहे हैं। वापस जाओ!",
            "इस अभिनेता के फैंस सचमुच बहुत घटिया और बदतमीज़ हैं। कोई काम-धंधा नहीं है इन मूर्खों को।",
            "आजकल के न्यूज़ एंकर बिकाऊ मीडिया का हिस्सा हैं जो टीआरपी के लिए सिर्फ नफरत फैलाते हैं।",
            "इस कंपनी की सर्विस एकदम बकवास है। भगवान करे ये कंपनी जल्द ही बंद हो जाए।",
            "गजब के पाखंडी हैं! समानता की बात करते हैं और खुद अंदर से इतने पक्षपाती हैं।",
            "ये ऑनलाइन नफरत फैलाने वाले कायर हैं। सामने आने की इनकी हिम्मत नहीं है।"
        ],
        "incitement": [
            "अब हाथ पर हाथ धर कर बैठने का समय नहीं है। कल {city} चौक पर इकट्ठा हो जाओ और उनका दफ्तर फूंक दो। लाठियां साथ लाना!",
            "अगर पुलिस कोई कार्रवाई नहीं करेगी, तो हमें {city} के पास हाईवे जाम करना होगा और हर गाड़ी को तोड़ करना होगा।",
            "इस देशद्रोही को बीच सड़क पर जिंदा जला देना चाहिए। इसका {city} का पता निकालो और इसे सबक सिखाओ।",
            "इस शुक्रवार {city} के सरकारी दफ्तर पर धावा बोलो। तोड़फोड़ करो और इन अफसरों को बाहर खदेड़ो।",
            "शांतिपूर्ण बातें खत्म। अब हिंसा का जवाब हिंसा से देना होगा। आज रात उनके गोदामों में आग लगा दो!",
            "अगर वे हमारे {city} के इलाके में दिखे, तो वे वापस नहीं जाने चाहिए। हथियार उठाओ और तैयार रहो।",
            "उनकी गाड़ियों को रोककर उनमें आग लगा दो और माल लूट लो। तबाही मचा दो!",
            "इन गद्दारों को घरों से घसीटकर बाहर निकालो और मारो। असली सबक सिखाने का वक्त आ गया है।",
            "मैं तुम्हें बर्बाद कर दूंगा। बच कर रहना।",
            "तुम बच नहीं पाओगे, तुम्हें जान से मार दूंगा।",
            "कल उन लोगों को मार देना चाहिए। सबक सिखाओ।"
        ],
        "fake_news": [
            "ब्रेकिंग: सरकारी गुप्त दस्तावेज़ लीक! {city} में आज रात 12 बजे से पूरी तरह इंटरनेट बंद रहेगा। कैश निकाल लें!",
            "सावधान: रिसर्च से पता चला है कि {city} के नगर निगम के पानी में जानबूझकर कोई ज़हरीला रसायन मिलाया जा रहा है।",
            "चेतावनी: {city} के पास एक बड़ी फैक्ट्री से गैस रिसाव हुआ है। प्रशासन मौतों का आंकड़ा छुपाने की कोशिश कर रहा है!",
            "लीक रिपोर्ट: {city} का एक बड़ा बैंक दिवालिया होने वाला है। अपना सारा पैसा कल ही निकाल लें, नहीं तो डूब जाएगा!",
            "सावधान: इस हफ्ते बाज़ार से नमक न खरीदें। चीन से आया प्लास्टिक का नमक {city} में बेचा जा रहा है। जांच करें!",
            "बड़ी खबर: नासा की चेतावनी! अगले 48 घंटों में {city} और आसपास के इलाकों में बड़ा भूकंप आने वाला है। घर खाली कर दें!",
            "सनसनीखेज खुलासा: स्थानीय अस्पताल में नकली दवाओं का परीक्षण हो रहा है। वीडियो सोशल मीडिया पर वायरल।",
            "अंदर की खबर: चुनाव प्रभावित करने के लिए विदेशी ताकतें अगले हफ्ते {city} में दंगे भड़काने की प्लानिंग कर रही हैं।"
        ]
    },
    "gujarati": {
        "neutral": [
            "આજે {city} માં રિવરફ્રન્ટ પર ચાલવાની ખૂબ મજા આવી. સાંજનું વાતાવરણ એકદમ સરસ હતું.",
            "{city} ના આ નવા બ્રિજ અને ડેવલપમેન્ટ જોઈને ખૂબ આનંદ થયો. પ્રગતિ થઈ રહી છે.",
            "કોઈ કહી શકશે કે {city} માં ખાણી-પીણી માટે કઈ જગ્યાઓ બેસ્ટ છે?",
            "આ વીડિયો ખૂબ જ સરસ છે! બધી જ વિગતો સરળ ભાષામાં સમજાવી છે. ખૂબ આભાર.",
            "જો તમે {city} માં હોવ, તો અહીંનું પ્રખ્યાત મંદિર અને મ્યુઝિયમ જરૂર જોજો.",
            "ગઈકાલે રાત્રે {city} ના નાટક ઉત્સવમાં ખૂબ મજા આવી. કલાકારોએ અદભુત પ્રદર્શન કર્યું.",
            "શું કોઈને ખબર છે કે {city} ની સરકારી હોસ્પિટલમાં ઓપીડીનો સમય શું છે?",
            "ગુજરાતી ક્રિકેટરની શાનદાર રમત જોઈને દિલ ખુશ થઈ ગયું. ગર્વ છે!"
        ],
        "inflammatory": [
            "{city} ના આ નેતા સાવ નકામા છે, માત્ર ખોટા વાયદા કરી ભોળી જનતાને છેતરે છે. શરમ આવી જોઈએ.",
            "{city} મ્યુનિસિપલ કોર્પોરેશન સાવ ભ્રષ્ટ છે. રોડ-રસ્તા તો જુઓ, કરોડો રૂપિયા ક્યાં જાય છે કોઈને ખબર નથી.",
            "બહારના લોકો આવીને આપણા {city} ની શાંતિ અને સંસ્કૃતિ બગાડી રહ્યા છે. એમને પાછા મોકલો!",
            "આ કલાકારના ફેન્સ સાવ મગજ વગરના છે. દિવસ આખો સોશિયલ મીડિયા પર ગાળો જ બોલે છે.",
            "આજના ટીવી એન્કરો માત્ર નફરત ફેલાવી દેશને તોડવાનું કામ કરે છે. સાવ બિકાઉ મીડિયા છે.",
            "આ બ્રાન્ડની પ્રોડક્ટ સાવ ભંગાર છે. પૈસા વેડફાઈ ગયા. કોઈ ભૂલથી પણ આ ન ખરીદતા.",
            "ખૂબ મોટા ઢોંગી છે આ લોકો. ભાષણો સારા આપે છે પણ અંદરથી સાવ સ્વાર્થી અને પક્ષપાતી છે.",
            "આવા કાયર લોકો માત્ર કમેન્ટ સેક્શનમાં જ બહાદુરી બતાવે છે, બહાર નીકળવાની તાકાત નથી."
        ],
        "incitement": [
            "હવે સહન નથી થતું. આવતીકાલે {city} માં બધા ભેગા થઈને એમના ઘરો પર પથ્થરમારો કરો અને સળગાવી દો.",
            "જો તંત્ર પગલાં ન લે તો આપણે જ કાયદો હાથમાં લેવો પડશે. {city} હાઈવે પર ગાડીઓ રોકો અને હુમલો કરો.",
            "આ નરાધમને જીવતો રાખવાનો કોઈ મતલબ નથી. {city} માં એનું સરનામું શોધો અને એને પૂરું કરી નાખો.",
            "આ શુક્રવારે {city} ની સરકારી કચેરીમાં ઘૂસી જાવ. બધો સામાન તોડી નાખો અને ઓફિસરોને મારો.",
            "શાંતિથી કઈ વળશે નહીં. ઈંટનો જવાબ પથ્થરથી આપવાનો સમય આવી ગયો છે. આજે રાત્રે જ હુમલો કરો!",
            "જો એ લોકો આપણા {city} વિસ્તારમાં ઘૂસે તો પાછા જીવતા ન જવા જોઈએ. હથિયાર તૈયાર રાખો.",
            "એમની ટ્રકો અટકાવો, કાચ તોડો અને બધું સળગાવી દો. કોઈને છોડવાના નથી થતા.",
            "આ દેશદ્રોહીઓને પકડીને ધોકા મારો. ચાલો આજે જ એમના અડ્ડાઓ પર તૂટી પડીએ.",
            "હું તને બરબાદ કરી નાખીશ. બચીને રહેજે.",
            "તને મારી નાખીશ, તારો સમય પૂરો થઈ ગયો છે."
        ],
        "fake_news": [
            "બ્રેકિંગ ન્યૂઝ: સરકારનો ગુપ્ત આદેશ બહાર પડ્યો છે. {city} માં કાલે સવારથી જ પાણી કાપી નાખવામાં આવશે.",
            "સાવધાન: {city} ની આસપાસ શાકભાજીમાં કોઈ કેમિકલનું ઈન્જેક્શન મારીને માર્કેટમાં મોકલી રહ્યું છે, ન ખાવું!",
            "ચેતવણી: {city} ની નજીક ડેમમાં મોટી તિરાડ પડી છે, ગમે ત્યારે આખું શહેર ડૂબી શકે છે. જલ્દી ભાગો!",
            "ખાસ અહેવાલ: {city} ની મુખ્ય બેંક બંધ થવા જઈ રહી છે. આરબીઆઈએ લાયસન્સ રદ કર્યું. જલ્દી પૈસા ઉપાડી લો!",
            "મોટો ખુલાસો: બજારમાં પ્લાસ્ટિકના ઈંડા અને નકલી ચોખા ધૂમ વેચાઈ રહ્યા છે. {city} માં 20 લોકો બીમાર.",
            "ભૂકંપની ચેતવણી: વૈજ્ઞાનિકોની ભયાનક આગાહી, આગામી ૨૪ કલાકમાં {city} માં રેક્ટર સ્કેલ પર 7 નો ધરતીકંપ આવશે!",
            "વાયરલ વિડીયો સચ્ચાઈ: હોસ્પિટલોમાં નકલી કીટ વાપરી રિપોર્ટ પોઝિટિવ બતાવી લૂંટ ચલાવાઈ રહી છે.",
            "સનસનીખેજ માહિતી: વિપક્ષી નેતાઓ વિદેશી ગુપ્ત એજન્સીઓ સાથે મળીને {city} માં તોફાનો કરાવવા મીટિંગ કરી રહ્યા છે."
        ]
    },
    "hinglish": {
        "neutral": [
            "Had a great experience visiting Sabarmati Riverfront in {city} today! Weather was super chill.",
            "Just saw the new double-decker flyover in {city}. Infrastructure update is looking dope.",
            "Guys, can someone recommend the best Gujarati thali spot in {city}?",
            "This YouTube video is so helpful, direct point to point bataya hai bina time waste kiye. Nice!",
            "If you ever go to {city}, must check out the historical pol area. Absolutely beautiful.",
            "Last night {city} cultural event was amazing. Food stalls were especially awesome.",
            "Does anyone know if {city} public garden is open early morning around 5 AM?",
            "Match highlights dekhe abhi, what a crazy win by team. Fully deserved victory!"
        ],
        "inflammatory": [
            "Yeh local leader of {city} is an absolute fraud. Jo inko support karte hain, wo dimaag se khali hain.",
            "{city} municipal corporation is completely corrupt. Roads are full of potholes and money is gone.",
            "Seriously, outside state ke log aakar {city} ki local culture spoil kar rahe hain. Inko wapas bhejo.",
            "This influencer has such brainless fans. Comments me bas toxicity failate hain pure din, fools.",
            "Aaj kal ke news channels are just selling trash. TRP ke liye kuch bhi faltu debate dikhate hain.",
            "This app's customer support is total garbage. Spent 2 hours and got zero help. Uninstalling!",
            "Huge hypocrites! Badi badi baatein karte hain and real life me itna bias display karte hain.",
            "These online trolls are just cowards. Desktop ke peeche baith ke shana bante hain, samne aao toh phat jaye.",
            "modi sarkar ne sab barbaad kar diya"
        ],
        "incitement": [
            "We have tolerated enough. Kal sab log {city} bypass pe milo, inki gadiyon ko aag lagani hai. Bring petrol!",
            "If authority action nahi legi, toh hume hi rasta rokna hoga. Block the main bridge in {city} and smash everything.",
            "This guy deserves to be beaten to death. Find his office in {city} and thrash him in public.",
            "Let's raid the corporate office in {city} this Monday. Break everything and beat up the managers.",
            "Peaceful protest se kuch nahi hoga. Violence ka jawab violence se dena padega. Burn down their shops tonight!",
            "Agar ye log hamare {city} wale area me aaye, toh safely wapas nahi jaane chahiye. Get ready with weapons.",
            "Inke trucks ko raste me roko, windshield tod do aur driver ko peeto. Show them our power!",
            "Let's drag these traitors out of their houses and beat them up. Time for action, no more talking.",
            "I will destroy you. Watch your back.",
            "Tumhe jaan se maar dunga. Tum bach nahi paoge.",
            "kal un logo ko maar dena chahiye"
        ],
        "fake_news": [
            "BREAKING: Secret government notification out! Social media is getting banned in {city} from tonight. Alert!",
            "WARNING: Do not drink local supply water in {city}. Industrial chemical mix ho chuka hai, dangerous!",
            "ALERT: Big dam near {city} is cracking. Water can flood the low areas in next 3 hours. Evacuate immediately!",
            "Leaked news: This major cooperative bank in {city} is locking doors tomorrow. Withdraw your cash ASAP!",
            "ALERT: Fake plastic rice is being sold in {city} grocery markets. Please share this warning with everyone.",
            "Big Alert: Meteorological department warns of major 6.8 earthquake in {city} zone tonight. Stay outside houses!",
            "Shocking expose: Private hospitals are using fake testing kits. Video proof going viral on WhatsApp.",
            "Secret source: Riot squads are being placed secretly because riots are pre-planned in {city} next week."
        ]
    },
    "gujlish": {
        "neutral": [
            "Riverfront par walk karvani full maza avi gayi aaj to in {city}. Superb weather.",
            "Just saw the new shopping mall construction in {city}. Infrastructure growth is amazing.",
            "Friends, can you suggest best locations for street food in {city}?",
            "This YouTube video series is too good. Coding logic ekdum simple language ma samjavyo chhe.",
            "If you visit {city}, do not miss the local traditional market. Worth shopping there.",
            "Yesterday night {city} youth festival was superb. Music and energy were next level.",
            "Does anyone know if {city} botanical garden allows DSLR cameras inside?",
            "Match na highlights joya, historical win chhe. Team performance was outstanding!"
        ],
        "inflammatory": [
            "Aa local authority in {city} is total waste. Eni pase kam karvavani badhi ummid bekar chhe. Idiots.",
            "{city} SMC is super corrupt. Badha rasta par khada chhe and budget kyan gayu koi boltu nathi.",
            "Honestly, outside na loko aavi ne {city} nu environment kharab kare chhe. Send them back!",
            "Aa vlogger na followers toh ekdum basic sense vagarna chhe. Faltu comment kariya kare chhe badhe.",
            "Most media channels are just fake and biased. Biko-la loko chhe, paisa mate game te news dekhade.",
            "Aa brand ni product ekdum useless chhe. Mara badha money waste thai gaya. Never buy this.",
            "Ketla mota hypocrites chhe aa loko. Lectures aape chhe and pota na actions ma zero logic chhe.",
            "Aa online haters badha bick-la chhe. keyboard par mothi vaato kare and real ma bhed thai jaye."
        ],
        "incitement": [
            "Aa loko limits cross kare chhe. Kale {city} na main circle par bhega thao and aemni office todi nakho. Danda lavjo!",
            "If police is not doing anything, we have to start. {city} ma road block karo ane badhi gadiyo todva mando.",
            "Aane toh rasta par ghasdi ne marvo joie. {city} ma aeno flat number nikaljo ane jaine thoki aavo.",
            "Let's attack the municipal office in {city} this Wednesday. Badhi files bhadkavi do ane babuo ne peeto.",
            "No more silent requests. Aa loko mar khava na j chhe. Aemni dukan sળgavi do aaje raatre j!",
            "Agar aa loko aaprna {city} na complex ma avse toh mar khaine j jashe. Tayar raho badha danda sathe.",
            "Aemna vehicles roko, windshield todo ane aag lagavo. Have vaato nai directly dhoka maro.",
            "Drag these traitors out and teach them a lesson. Vadhu vicharva vagar kale j aemna aaddao par danga karo.",
            "Tane mari nakhiyo. Tari life puri kari daish.",
            "Tane barbad kari nakhiyo, joi leje tu.",
            "Aa loko ne desh mathi kadhi nakho."
        ],
        "fake_news": [
            "BREAKING: Secret administrative circular leaked! Complete blackout in {city} for 3 days starting tonight.",
            "WARNING: Do not eat raw leafy vegetables in {city}. Local fields ma chemical water spray thaye chhe.",
            "ALERT: Water levels in {city} reservoir crossed danger mark. Dam lock broken. High alert in low lying areas!",
            "Leaked info: Aa moti bank in {city} is going to crash. RBI and clear command aapyu chhe, withdraw all savings!",
            "ALERT: Fake synthetic milk made of detergent and oil is captured in {city} raid. Don't buy loose milk!",
            "Major Alert: Earthquake warning issued for {city} zone. 6.5 magnitude expected between 2 AM to 4 AM. Share!",
            "Viral Expose: Government is secretly injecting expired vaccines. Doctors video leaked from {city} clinic.",
            "Internal report: Artificial civil riots will be triggered in {city} next week by paid political agents. Stay safe!"
        ]
    }
}

# Helper to generate random timestamps in the last 30 days
def generate_random_timestamp():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    random_days = random.random() * 30
    random_date = start_date + timedelta(days=random_days)
    return random_date.isoformat()

# Helper to generate random engagement metrics
def generate_engagement(platform):
    if platform == "X":
        likes = random.randint(0, 12000)
        retweets = int(likes * random.uniform(0.1, 0.4))
        replies = int(likes * random.uniform(0.05, 0.2))
        return {"likes": likes, "shares": retweets, "comments": replies}
    elif platform == "Instagram":
        likes = random.randint(0, 25000)
        comments = int(likes * random.uniform(0.02, 0.08))
        return {"likes": likes, "shares": random.randint(0, 500), "comments": comments}
    elif platform == "Facebook":
        likes = random.randint(0, 8000)
        shares = int(likes * random.uniform(0.05, 0.15))
        comments = int(likes * random.uniform(0.1, 0.3))
        return {"likes": likes, "shares": shares, "comments": comments}
    else:  # YouTube
        likes = random.randint(0, 45000)
        comments = int(likes * random.uniform(0.05, 0.15))
        return {"likes": likes, "shares": 0, "comments": comments}  # YouTube shares not easily simulated

# Helper to generate user profiles with age and followers/following ratio
def generate_user_profile(is_coordinated=False):
    now = datetime.now()
    if is_coordinated:
        # bot account: created in the last 30 days, high following count but extremely low follower count
        created_days_ago = random.randint(2, 30)
        created_date = (now - timedelta(days=created_days_ago)).strftime("%Y-%m-%d")
        followers = random.randint(1, 25)
        following = random.randint(450, 1200)
    else:
        # normal account: created long ago (1 - 5 years), normal ratio
        created_days_ago = random.randint(365, 365 * 5)
        created_date = (now - timedelta(days=created_days_ago)).strftime("%Y-%m-%d")
        followers = random.randint(100, 45000)
        following = random.randint(50, 1500)
        
    return {
        "account_created_date": created_date,
        "follower_count": followers,
        "following_count": following
    }

def generate_post_id(index):
    return f"post_{index:04d}"

def main():
    print("Starting synthetic data generation...")
    
    posts = []
    post_index = 1
    
    # We want ~500 posts. 
    # With 5 languages and 4 categories = 20 cells.
    # To get exactly 500 posts, we generate exactly 25 posts per cell (20 * 25 = 500).
    target_per_cell = 25
    
    for lang in LANGUAGES:
        for cat in CATEGORIES:
            templates = TEMPLATES[lang][cat]
            
            for i in range(target_per_cell):
                # Choose a template
                template = random.choice(templates)
                
                # Pick a random city
                city_obj = random.choice(CITIES)
                city_name = city_obj["name"]
                
                # Interpolate placeholders
                text = template.format(city=city_name)
                
                # Randomize platform
                platform = random.choice(PLATFORMS)
                
                # Randomize username
                username = random.choice(USERNAMES_POOL)
                if platform == "X" or platform == "Instagram":
                    username = f"@{username}"
                
                # Randomize timestamp
                timestamp = generate_random_timestamp()
                
                # Randomize engagement
                engagement = generate_engagement(platform)
                
                # Add minor perturbations to avoid duplicates
                emojis = ["😊", "👍", "🔥", "⚠️", "🚨", "😮", "😡", "👀", "💔", "🤔", "🙌", "💀"]
                hashtags = {
                    "neutral": ["#Development", "#LocalInfo", "#Travel", "#BeautifulIndia", "#Community"],
                    "inflammatory": ["#Unfair", "#Frustrated", "#Exposed", "#WakeUp", "#NoRespect"],
                    "incitement": ["#ActionNow", "#Revolt", "#TakeOver", "#TimeIsNow", "#NoMoreWaiting"],
                    "fake_news": ["#BreakingNews", "#Expose", "#ViralAlert", "#Alert", "#ShockingInfo"]
                }
                
                # 40% chance to append an emoji or hashtag
                suffix = ""
                if random.random() < 0.4:
                    emoji = random.choice(emojis)
                    suffix += f" {emoji}"
                if random.random() < 0.4:
                    hashtag = random.choice(hashtags[cat])
                    suffix += f" {hashtag}"
                    
                text += suffix
                
                post = {
                    "id": generate_post_id(post_index),
                    "username": username,
                    "platform": platform,
                    "timestamp": timestamp,
                    "text": text,
                    "language": lang,
                    "threat_category": cat,
                    "engagement": engagement,
                    "geo": {
                        "city": city_name,
                        "latitude": round(city_obj["lat"] + random.uniform(-0.02, 0.02), 4),
                        "longitude": round(city_obj["lon"] + random.uniform(-0.02, 0.02), 4)
                    },
                    "user_profile": generate_user_profile(is_coordinated=False)
                }
                
                posts.append(post)
                post_index += 1

    # ==========================================
    # SEEDING DELIBERATE COORDINATED POST CAMPAIGNS
    # ==========================================
    
    # Campaign Cluster 1: Templated Disinformation (Fake News)
    # 4 accounts posting nearly identical Fake News statements about a Gandhinagar factory chemical leak.
    # Posted spaced 30 seconds apart. Users are bots (very recent account, bad ratio).
    base_time_c1 = datetime.now() - timedelta(days=4, hours=2)
    c1_texts = [
        "ALERT: Major chemical leak near Gandhinagar factory is causing breathing issues! Stay safe. #Gandhinagar 🚨",
        "ALERT: Major chemical leak near Gandhinagar factory is causing breathing issues! Stay safe. #Gandhinagar ⚠️",
        "ALERT: Major chemical leak near Gandhinagar factory is causing breathing issues! Stay safe. #Gandhinagar 🛑",
        "ALERT: Major chemical leak near Gandhinagar factory is causing breathing issues! Stay safe. #Gandhinagar 🚫"
    ]
    c1_users = ["@bot_agent_01", "@bot_agent_02", "@bot_agent_03", "@bot_agent_04"]
    for idx, text in enumerate(c1_texts):
        post_time = (base_time_c1 + timedelta(seconds=idx * 30)).isoformat()
        posts.append({
            "id": generate_post_id(post_index),
            "username": c1_users[idx],
            "platform": "X",
            "timestamp": post_time,
            "text": text,
            "language": "english",
            "threat_category": "fake_news",
            "engagement": {"likes": random.randint(10, 50), "shares": random.randint(5, 20), "comments": random.randint(1, 10)},
            "geo": {
                "city": "Gandhinagar",
                "latitude": 23.2156,
                "longitude": 72.6369
            },
            "user_profile": generate_user_profile(is_coordinated=True)
        })
        post_index += 1

    # Campaign Cluster 2: Synchronized Violence Incitement (Incitement)
    # 5 accounts posting aggressive violence threats within 5 seconds of each other.
    base_time_c2 = datetime.now() - timedelta(days=2, hours=5)
    c2_texts = [
        "Chalo kale aeni office todi nakhiye! #ActionNow 🔥",
        "Everyone gather at Rajkot circle tomorrow, bring weapons! #Revolt 💀",
        "Burn down their trucks, don't let anyone escape! #Revolt 😡",
        "Show them our power. Vandalize their shops tonight! #ActionNow 🔥",
        "Drag these traitors out of their houses and beat them up! #Revolt 😡"
    ]
    c2_users = ["@sync_user_a", "@sync_user_b", "@sync_user_c", "@sync_user_d", "@sync_user_e"]
    for idx, text in enumerate(c2_texts):
        post_time = (base_time_c2 + timedelta(seconds=idx + random.uniform(0.1, 1.5))).isoformat()
        posts.append({
            "id": generate_post_id(post_index),
            "username": c2_users[idx],
            "platform": "Instagram",
            "timestamp": post_time,
            "text": text,
            "language": "gujlish",
            "threat_category": "incitement",
            "engagement": {"likes": random.randint(5, 25), "shares": random.randint(1, 5), "comments": random.randint(2, 8)},
            "geo": {
                "city": "Rajkot",
                "latitude": 22.3039,
                "longitude": 70.8022
            },
            "user_profile": generate_user_profile(is_coordinated=True)
        })
        post_index += 1
        
    # Shuffle the dataset to mix things up
    random.shuffle(posts)
    
    # Save dataset to data/sample_posts.json
    output_path = os.path.join("data", "sample_posts.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
        
    print(f"Successfully generated {len(posts)} posts (including seeded clusters) and saved to {output_path}")

if __name__ == "__main__":
    main()
