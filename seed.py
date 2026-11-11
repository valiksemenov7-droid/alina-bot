"""Initial content from the ТЗ. Services/categories are seeded once (empty DB); new text keys are added on every start."""
import db
from strings import DIV

IG_LINK = '<a href="https://www.instagram.com/alina_cosmo__">@alina_cosmo__</a>'  # clickable link, not a Telegram @mention

CATS = [
    ("face", ("Уходовые и аппаратные процедуры лица", "Cuidado y aparatología facial", "Facial care & device treatments")),
    ("inject", ("Инъекционные процедуры", "Procedimientos inyectables", "Injectable treatments")),
    ("inject", ("Препараты и бустеры", "Productos y boosters", "Products & boosters")),
    ("body", ("Аппаратная коррекция тела и комплексы", "Aparatología corporal y packs", "Body device treatments & packages")),
]

ML = ("за 1 мл", "por 1 ml", "per 1 ml")
ZONE = ("за зону; курс — только после консультации", "por zona; curso solo tras consulta", "per area; course only after consultation")
SAVE125 = ("курс действует 2 месяца с даты покупки; экономия 125 €",
           "curso válido 2 meses desde la compra; ahorro de 125 €",
           "course valid for 2 months from purchase; you save €125")
SAVE330 = ("курс действует 2 месяца с даты покупки; экономия 330 €",
           "curso válido 2 meses desde la compra; ahorro de 330 €",
           "course valid for 2 months from purchase; you save €330")

DESC_BOTOX = (
    "Ботулинический токсин типа A временно уменьшает активность определённых мимических мышц. Зоны, показания, "
    "противопоказания и интервалы зависят от конкретного препарата и определяются специалистом по его официальной "
    "инструкции. Возможные зоны: лоб, межбровье, область вокруг глаз, подбородок, brow lift.",
    "La toxina botulínica tipo A reduce temporalmente la actividad de ciertos músculos de la expresión. Las zonas, "
    "indicaciones, contraindicaciones e intervalos dependen del producto concreto y los determina el especialista "
    "según sus instrucciones oficiales. Zonas posibles: frente, entrecejo, contorno de ojos, mentón y brow lift.",
    "Botulinum toxin type A temporarily reduces the activity of certain facial muscles. Treatment areas, indications, "
    "contraindications and intervals depend on the specific product and are determined by the specialist according to "
    "its official instructions. Possible areas: forehead, glabella, around the eyes, chin and brow lift.",
)
DESC_FILLER = (
    "Контурная коррекция выполняется подходящим филлером, например на основе гиалуроновой кислоты, если именно такой "
    "продукт применяется. Возможные зоны: губы, скулы, подбородок, углы нижней челюсти, носогубные и марионеточные "
    "складки, слёзная борозда. Препарат и объём подбирает специалист на консультации.",
    "La corrección de contornos se realiza con un relleno adecuado, por ejemplo a base de ácido hialurónico, si es ese "
    "el producto utilizado. Zonas posibles: labios, pómulos, mentón, ángulos mandibulares, surcos nasogenianos y líneas "
    "de marioneta, surco lagrimal. El producto y el volumen los elige el especialista en la consulta.",
    "Contour correction is performed with a suitable filler, for example hyaluronic acid–based, if that is the product "
    "used. Possible areas: lips, cheekbones, chin, jaw angles, nasolabial folds and marionette lines, tear trough. The "
    "product and volume are chosen by the specialist during the consultation.",
)


def svc(cat, names, price="", frm=0, old="", note=None, ok=1, admin="", desc=None):
    return dict(cat=cat, names=names, price=price, frm=frm, old=old, note=note or ("", "", ""), ok=ok, admin=admin, desc=desc)


SERVICES = [
    # 1 — face
    svc(1, ("Ультразвуковая чистка лица", "Limpieza facial ultrasónica", "Ultrasonic facial cleansing"), "30 €"),
    svc(1, ("Пилинг по типу кожи", "Peeling según el tipo de piel", "Peeling by skin type"), "30 €"),
    svc(1, ("Карбоновый пилинг", "Peeling de carbono", "Carbon peel"), "40 €", admin="Уточнить оборудование и технологию"),
    svc(1, ("RF-лифтинг лица", "Lifting facial RF", "RF face lifting"), "50 €"),
    svc(1, ("Безынъекционная процедура", "Tratamiento no inyectable", "Non-injection treatment"), "50 €", frm=1,
        admin="Уточнить метод и используемые средства"),
    svc(1, ("Микронидлинг + витаминный комплекс", "Microneedling + complejo vitamínico", "Microneedling + vitamin complex"), "70 €"),
    # 2 — injectables
    svc(2, ("Увеличение губ", "Aumento de labios", "Lip augmentation"), "150–250 €", note=ML, ok=0, desc=DESC_FILLER,
        admin="150–250 € за 1 мл по позднему прайсу; во флаере 150–300 €. Подтвердить диапазон и цена за мл или за процедуру."),
    svc(2, ("Контурная коррекция филлерами", "Corrección de contornos con rellenos", "Contour correction with fillers"),
        "150–250 €", note=ML, ok=0, desc=DESC_FILLER,
        admin="150–250 € за 1 мл по позднему прайсу; во флаере 150–300 €. Подтвердить."),
    svc(2, ("Коррекция слёзной борозды", "Corrección del surco lagrimal", "Tear trough correction"), "150–250 €", desc=DESC_FILLER),
    svc(2, ("Ботокс, 1 зона", "Bótox, 1 zona", "Botox, 1 area"), "60–80 €", ok=0, desc=DESC_BOTOX,
        admin="60–80 €; также фигурировала цена 60 €. Подтвердить."),
    svc(2, ("Ботокс: лоб + межбровье + глаза", "Bótox: frente + entrecejo + ojos", "Botox: forehead + glabella + eyes"),
        "150 €", old="180 €", ok=0, desc=DESC_BOTOX, admin="Акция 150 € вместо 180 € — подтвердить, действует ли."),
    svc(2, ("Botox Full Face", "Botox Full Face", "Botox Full Face"), "250 €", old="350 €", ok=0, desc=DESC_BOTOX,
        admin="250 € по обновлённому прайсу; в старом флаере 350 €. Подтвердить."),
    svc(2, ("Full Face (филлеры)", "Full Face (rellenos)", "Full Face (fillers)"), "400 €", frm=1, desc=DESC_FILLER),
    svc(2, ("Full Face Premium: 3 зоны филлера + 3 зоны ботулотоксина",
            "Full Face Premium: 3 zonas de relleno + 3 zonas de toxina botulínica",
            "Full Face Premium: 3 filler areas + 3 botulinum toxin areas"), "500 €"),
    svc(2, ("Биоревитализация", "Biorrevitalización", "Biorevitalization"), "100–200 €"),
    svc(2, ("Мезотерапия", "Mesoterapia", "Mesotherapy"), "80–120 €"),
    svc(2, ("Полимолочная кислота (PLLA)", "Ácido poliláctico (PLLA)", "Poly-L-lactic acid (PLLA)"), "300–500 €",
        admin="Проверить точный бренд и официальную инструкцию"),
    svc(2, ("Липолитики", "Lipolíticos", "Lipolytics"), "30–60 €", note=ZONE),
    # 3 — products & boosters
    svc(3, ("Rejuran I — периорбитальная зона", "Rejuran I — zona periocular", "Rejuran I — periorbital area"), "120 €"),
    svc(3, ("Lapiena PN Eyes", "Lapiena PN Eyes", "Lapiena PN Eyes"), "95 €"),
    svc(3, ("GANA Eye Booster", "GANA Eye Booster", "GANA Eye Booster"), "95 €"),
    svc(3, ("Plinest Eye", "Plinest Eye", "Plinest Eye"), "160 €"),
    svc(3, ("MIORE Booster — периорбитальная зона", "MIORE Booster — zona periocular", "MIORE Booster — periorbital area"), "60 €"),
    svc(3, ("Plenhyage XL Strong", "Plenhyage XL Strong", "Plenhyage XL Strong"), "150 €"),
    svc(3, ("Nucleofill Strong", "Nucleofill Strong", "Nucleofill Strong"), "140 €"),
    svc(3, ("Авторский коктейль 5 мл, лицо + шея", "Cóctel de autor 5 ml, rostro + cuello", "Signature cocktail 5 ml, face + neck"),
        "200 €", ok=0, admin="Проверить состав, изготовителя, стерильность и допустимый способ применения до публикации."),
    svc(3, ("MIORE PNV / Mesolift / Booster", "MIORE PNV / Mesolift / Booster", "MIORE PNV / Mesolift / Booster"), "120 €"),
    # 4 — body
    svc(4, ("Вакуумный массаж", "Masaje al vacío", "Vacuum massage"), ok=0, admin="Уточнить отдельную цену"),
    svc(4, ("Кавитация", "Cavitación", "Cavitation"), ok=0, admin="Уточнить отдельную цену"),
    svc(4, ("RF-лифтинг тела", "Lifting corporal RF", "RF body lifting"), ok=0, admin="Уточнить отдельную цену"),
    svc(4, ("Лимфодренажный массаж", "Drenaje linfático", "Lymphatic drainage massage"), ok=0,
        admin="Входит в Premium; уточнить цену и метод (ручной или аппаратный)."),
    svc(4, ("Slim Start: кавитация + вакуумный массаж", "Slim Start: cavitación + masaje al vacío", "Slim Start: cavitation + vacuum massage"),
        "45 €", old="55 €"),
    svc(4, ("Body Sculpt: кавитация + вакуумный массаж + RF", "Body Sculpt: cavitación + masaje al vacío + RF", "Body Sculpt: cavitation + vacuum massage + RF"),
        "60 €", old="75 €"),
    svc(4, ("Anti-Cellulite Premium: кавитация + вакуум + RF + лимфодренаж",
            "Anti-Cellulite Premium: cavitación + vacío + RF + drenaje linfático",
            "Anti-Cellulite Premium: cavitation + vacuum + RF + lymphatic drainage"), "75 €", old="95 €"),
    svc(4, ("Body Sculpt — 5 процедур", "Body Sculpt — 5 sesiones", "Body Sculpt — 5 sessions"), "240 €"),
    svc(4, ("Body Sculpt — 10 процедур", "Body Sculpt — 10 sesiones", "Body Sculpt — 10 sessions"), "420 €"),
    svc(4, ("Антицеллюлитный курс — 5 процедур", "Curso anticelulítico — 5 sesiones", "Anti-cellulite course — 5 sessions"),
        "250 €", note=SAVE125, admin="Подтвердить правила переносов/возвратов."),
    svc(4, ("Антицеллюлитный курс — 10 процедур", "Curso anticelulítico — 10 sesiones", "Anti-cellulite course — 10 sessions"),
        "420 €", note=SAVE330, admin="Подтвердить правила переносов/возвратов."),
]

# key, admin label, ru, es, en, needs_review
TEXTS = [
    ("welcome", "Приветствие",
     "Добро пожаловать в <b>ALINA BEAUTY ESTHETIC</b> ✨\nЯ — виртуальный ассистент студии: расскажу об услугах, покажу прайс и помогу оставить заявку на запись.\n\nTorrevieja, Alicante, España 🇪🇸",
     "Bienvenido/a a <b>ALINA BEAUTY ESTHETIC</b> ✨\nSoy el asistente virtual del estudio: le cuento sobre los servicios, le muestro los precios y le ayudo a solicitar una cita.\n\nTorrevieja, Alicante, España 🇪🇸",
     "Welcome to <b>ALINA BEAUTY ESTHETIC</b> ✨\nI'm the studio's virtual assistant: I'll tell you about our services, show prices and help you request an appointment.\n\nTorrevieja, Alicante, Spain 🇪🇸", 0),
    ("privacy", "Уведомление о персональных данных",
     "🔒 Продолжая, вы соглашаетесь на обработку персональных данных (имя, телефон), которые вы указываете для записи. Они используются только для связи с вами по заявке.",
     "🔒 Al continuar, acepta el tratamiento de los datos personales (nombre, teléfono) que facilita para la cita. Se utilizan solo para contactar con usted sobre su solicitud.",
     "🔒 By continuing, you agree to the processing of the personal data (name, phone) you provide for booking. It is used only to contact you about your request.", 0),
    ("privacy_url", "Ссылка на политику конфиденциальности (одна для всех языков)", "", "", "", 0),
    ("contacts", "Контакты",
     "📍 <b>ALINA BEAUTY ESTHETIC</b>\nTorrevieja, Alicante, España\n📞 +34 655 564 351\n📷 Instagram: " + IG_LINK,
     "📍 <b>ALINA BEAUTY ESTHETIC</b>\nTorrevieja, Alicante, España\n📞 +34 655 564 351\n📷 Instagram: " + IG_LINK,
     "📍 <b>ALINA BEAUTY ESTHETIC</b>\nTorrevieja, Alicante, Spain\n📞 +34 655 564 351\n📷 Instagram: " + IG_LINK, 0),
    ("hours", "Рабочие часы", "уточняйте у администратора", "consulte con la administración", "please ask the administrator", 0),
    ("windows", "Доступные окна для записи (необязательно)", "", "", "", 0),
    ("address", "Адрес (подставляется в подтверждение записи)",
     "Torrevieja, Alicante, España (точный адрес уточнит администратор)",
     "Torrevieja, Alicante, España (la administración le indicará la dirección exacta)",
     "Torrevieja, Alicante, Spain (the administrator will provide the exact address)", 0),
    ("promos", "Акции и комплексы",
     "🎁 <b>Акции и комплексы</b>\n\n• 10% скидка в день рождения\n• Приведи друга: вы оба получаете по 10%\n• Первичная консультация — бесплатно\n• Программа лояльности — условия уточняйте у администратора\n\nКомплексы для тела и пакеты процедур — в разделе «Аппаратная коррекция тела».",
     "🎁 <b>Promociones y packs</b>\n\n• 10 % de descuento en su cumpleaños\n• Traiga a una amiga: las dos obtienen un 10 %\n• Primera consulta gratuita\n• Programa de fidelidad: consulte las condiciones con la administración\n\nPacks corporales y bonos de sesiones, en la sección «Aparatología corporal».",
     "🎁 <b>Offers & packages</b>\n\n• 10% off on your birthday\n• Refer a friend: you both get 10%\n• First consultation is free\n• Loyalty programme — ask the administrator for details\n\nBody packages and session bundles are in the “Body device treatments” section.", 0),
    ("disclaimer", "Дисклеймер (внизу страниц услуг)",
     "ℹ️ Информация носит ознакомительный характер и не заменяет консультацию специалиста. Подбор процедуры — только индивидуально. Результат индивидуален и не гарантируется.",
     "ℹ️ La información es orientativa y no sustituye la consulta con el especialista. La selección del tratamiento es siempre individual. El resultado es individual y no está garantizado.",
     "ℹ️ This information is for general guidance only and does not replace a consultation with a specialist. Treatment selection is always individual. Results vary and are not guaranteed.", 0),
    ("safety_inject", "Предупреждение после инъекций",
     "🚑 После инъекционных процедур немедленно обратитесь за экстренной медицинской помощью (в Испании — 112) при: затруднении глотания, речи или дыхания; сильной или нарастающей боли; побледнении или необычном изменении цвета кожи; сетчатом рисунке кожи; ухудшении зрения или любых зрительных симптомах. Затем сообщите студии.",
     "🚑 Tras un procedimiento inyectable, solicite atención médica urgente de inmediato (en España, 112) si presenta: dificultad para tragar, hablar o respirar; dolor intenso o creciente; palidez o cambio inusual del color de la piel; patrón reticulado en la piel; empeoramiento de la visión o cualquier síntoma visual. Después, avise al estudio.",
     "🚑 After injectable procedures, seek urgent medical help immediately (in Spain, call 112) if you have: difficulty swallowing, speaking or breathing; severe or increasing pain; paleness or unusual skin colour change; a net-like skin pattern; worsening vision or any visual symptoms. Then let the studio know.", 0),
    ("booking_prep", "Подготовка к процедуре (добавляется в подтверждение; утвердить у специалиста)", "", "", "", 1),
    ("n_confirmed", "Сообщение клиенту: запись подтверждена ({service}, {when}, {address})",
     "✅ <b>Запись подтверждена</b>\n\n💆 {service}\n🗓 {when}\n📍 {address}",
     "✅ <b>Cita confirmada</b>\n\n💆 {service}\n🗓 {when}\n📍 {address}",
     "✅ <b>Booking confirmed</b>\n\n💆 {service}\n🗓 {when}\n📍 {address}", 0),
    ("n_rescheduled", "Сообщение клиенту: запись перенесена",
     "🔁 <b>Запись перенесена</b>\n\n💆 {service}\n🗓 Новое время: {when}\n📍 {address}",
     "🔁 <b>Cita reprogramada</b>\n\n💆 {service}\n🗓 Nueva hora: {when}\n📍 {address}",
     "🔁 <b>Booking rescheduled</b>\n\n💆 {service}\n🗓 New time: {when}\n📍 {address}", 0),
    ("n_cancelled", "Сообщение клиенту: запись отменена",
     "❌ Ваша запись ({service}) отменена. Чтобы выбрать другое время, нажмите «Записаться» в меню.",
     "❌ Su cita ({service}) ha sido cancelada. Para elegir otra hora, pulse «Reservar cita» en el menú.",
     "❌ Your booking ({service}) has been cancelled. To choose another time, tap “Book an appointment” in the menu.", 0),
    ("faq1_q", "FAQ 1 — вопрос", "Как записаться?", "¿Cómo reservar una cita?", "How do I book?", 0),
    ("faq1_a", "FAQ 1 — ответ",
     "Нажмите «Записаться», укажите услугу и удобное время. Студия подтвердит запись отдельно.",
     "Pulse «Reservar cita», indique el servicio y la hora que le venga bien. El estudio confirmará la cita por separado.",
     "Tap “Book an appointment”, choose the service and your preferred time. The studio will confirm your booking separately.", 0),
    ("faq2_q", "FAQ 2 — вопрос", "Какая процедура мне подойдёт?", "¿Qué tratamiento me conviene?", "Which treatment is right for me?", 0),
    ("faq2_a", "FAQ 2 — ответ",
     "Я помогу ознакомиться с услугами, но индивидуальный подбор возможен только после консультации со специалистом (первичная консультация бесплатная).",
     "Puedo ayudarle a conocer los servicios, pero la selección individual solo es posible tras una consulta con el especialista (la primera consulta es gratuita).",
     "I can help you explore the services, but individual selection is only possible after a consultation with the specialist (the first consultation is free).", 0),
    ("faq3_q", "FAQ 3 — вопрос", "Есть ли противопоказания?", "¿Hay contraindicaciones?", "Are there any contraindications?", 0),
    ("faq3_a", "FAQ 3 — ответ",
     "Да, они зависят от процедуры, продукта/аппарата и состояния клиента. Обсудите важную информацию со специалистом до визита.",
     "Sí, dependen del tratamiento, del producto o aparato y del estado de cada persona. Comente la información importante con el especialista antes de la visita.",
     "Yes — they depend on the treatment, the product/device and the client's condition. Please discuss any important information with the specialist before your visit.", 0),
    ("faq4_q", "FAQ 4 — вопрос", "Сколько держится результат?", "¿Cuánto dura el resultado?", "How long does the result last?", 0),
    ("faq4_a", "FAQ 4 — ответ",
     "Срок индивидуален и зависит от процедуры, продукта и особенностей организма.",
     "La duración es individual y depende del tratamiento, del producto y de las características de cada persona.",
     "Duration is individual and depends on the treatment, the product and your body's characteristics.", 0),
    ("faq5_q", "FAQ 5 — вопрос", "Как перенести запись?", "¿Cómo cambiar mi cita?", "How do I reschedule?", 0),
    ("faq5_a", "FAQ 5 — ответ",
     "Напишите студии; перенос подтверждает администратор.",
     "Escriba al estudio; el cambio lo confirma la administración.",
     "Message the studio; the administrator confirms the change.", 0),
]

DESIGN_VERSION = 3
# Restyled texts (emoji, dividers, structure). Applied to a fresh DB and once to an older DB (see run()).
DESIGN = {
    "welcome": (
        "✨ <b>ALINA BEAUTY ESTHETIC</b> ✨\n" + DIV + "\nДобро пожаловать! 🤍\nЯ — виртуальный ассистент студии: расскажу об услугах, покажу прайс и помогу записаться на процедуру.\n\n📍 Torrevieja, Alicante, España",
        "✨ <b>ALINA BEAUTY ESTHETIC</b> ✨\n" + DIV + "\n¡Bienvenido/a! 🤍\nSoy el asistente virtual del estudio: le cuento sobre los servicios, le muestro los precios y le ayudo a reservar su cita.\n\n📍 Torrevieja, Alicante, España",
        "✨ <b>ALINA BEAUTY ESTHETIC</b> ✨\n" + DIV + "\nWelcome! 🤍\nI'm the studio's virtual assistant: I'll tell you about our services, show prices and help you book an appointment.\n\n📍 Torrevieja, Alicante, Spain"),
    "privacy": (
        "🔒 <i>Продолжая, вы соглашаетесь на обработку персональных данных (имя, телефон), которые указываете для записи. Они используются только для связи с вами по заявке.</i>",
        "🔒 <i>Al continuar, acepta el tratamiento de los datos personales (nombre, teléfono) que facilita para la cita. Se utilizan solo para contactar con usted sobre su solicitud.</i>",
        "🔒 <i>By continuing, you agree to the processing of the personal data (name, phone) you provide for booking. It is used only to contact you about your request.</i>"),
    "contacts": (
        "📍 <b>ALINA BEAUTY ESTHETIC</b>\n" + DIV + "\n🏙 Torrevieja, Alicante, España\n📞 +34 655 564 351\n📷 Instagram: " + IG_LINK,
        "📍 <b>ALINA BEAUTY ESTHETIC</b>\n" + DIV + "\n🏙 Torrevieja, Alicante, España\n📞 +34 655 564 351\n📷 Instagram: " + IG_LINK,
        "📍 <b>ALINA BEAUTY ESTHETIC</b>\n" + DIV + "\n🏙 Torrevieja, Alicante, Spain\n📞 +34 655 564 351\n📷 Instagram: " + IG_LINK),
    "promos": (
        "🎁 <b>Акции и бонусы</b>\n" + DIV + "\n🎂 <b>День рождения</b> — скидка 10%\n👯 <b>Приведи друга</b> — по 10% вам обоим\n🩺 <b>Первая консультация</b> — бесплатно\n💎 <b>Программа лояльности</b> — условия уточняйте у администратора\n\n🌿 Комплексы для тела и пакеты процедур — в разделе «Аппаратная коррекция тела».",
        "🎁 <b>Promociones y bonos</b>\n" + DIV + "\n🎂 <b>Cumpleaños</b> — 10 % de descuento\n👯 <b>Traiga a una amiga</b> — 10 % para las dos\n🩺 <b>Primera consulta</b> — gratuita\n💎 <b>Programa de fidelidad</b> — consulte las condiciones con la administración\n\n🌿 Packs corporales y bonos de sesiones, en la sección «Aparatología corporal».",
        "🎁 <b>Offers & bonuses</b>\n" + DIV + "\n🎂 <b>Birthday</b> — 10% off\n👯 <b>Refer a friend</b> — 10% off for you both\n🩺 <b>First consultation</b> — free\n💎 <b>Loyalty programme</b> — ask the administrator for details\n\n🌿 Body packages and session bundles are in the “Body device treatments” section."),
    "disclaimer": (
        "ℹ️ <i>Информация носит ознакомительный характер и не заменяет консультацию специалиста. Подбор процедуры — только индивидуально. Результат индивидуален и не гарантируется.</i>",
        "ℹ️ <i>La información es orientativa y no sustituye la consulta con el especialista. La selección del tratamiento es siempre individual. El resultado es individual y no está garantizado.</i>",
        "ℹ️ <i>This information is for general guidance only and does not replace a consultation with a specialist. Treatment selection is always individual. Results vary and are not guaranteed.</i>"),
    "safety_inject": (
        "🚑 <b>Важно после инъекций</b>\nНемедленно обратитесь за экстренной помощью (в Испании — <b>112</b>), если появились:\n▫️ затруднение глотания, речи или дыхания\n▫️ сильная или нарастающая боль\n▫️ побледнение или необычный цвет кожи\n▫️ сетчатый рисунок кожи\n▫️ ухудшение зрения или зрительные симптомы\nЗатем сообщите студии.",
        "🚑 <b>Importante tras inyecciones</b>\nSolicite atención médica urgente de inmediato (en España, <b>112</b>) si presenta:\n▫️ dificultad para tragar, hablar o respirar\n▫️ dolor intenso o creciente\n▫️ palidez o cambio inusual del color de la piel\n▫️ patrón reticulado en la piel\n▫️ empeoramiento de la visión o síntomas visuales\nDespués, avise al estudio.",
        "🚑 <b>Important after injections</b>\nSeek urgent medical help immediately (in Spain, call <b>112</b>) if you have:\n▫️ difficulty swallowing, speaking or breathing\n▫️ severe or increasing pain\n▫️ paleness or unusual skin colour change\n▫️ a net-like skin pattern\n▫️ worsening vision or visual symptoms\nThen let the studio know."),
    "n_confirmed": (
        "✅ <b>Запись подтверждена</b>\n" + DIV + "\n💆 <b>{service}</b>\n📅 {when}\n📍 {address}\n\nЖдём вас! 🤍",
        "✅ <b>Cita confirmada</b>\n" + DIV + "\n💆 <b>{service}</b>\n📅 {when}\n📍 {address}\n\n¡Le esperamos! 🤍",
        "✅ <b>Booking confirmed</b>\n" + DIV + "\n💆 <b>{service}</b>\n📅 {when}\n📍 {address}\n\nSee you soon! 🤍"),
    "n_rescheduled": (
        "🔁 <b>Запись перенесена</b>\n" + DIV + "\n💆 <b>{service}</b>\n📅 Новое время: {when}\n📍 {address}",
        "🔁 <b>Cita reprogramada</b>\n" + DIV + "\n💆 <b>{service}</b>\n📅 Nueva hora: {when}\n📍 {address}",
        "🔁 <b>Booking rescheduled</b>\n" + DIV + "\n💆 <b>{service}</b>\n📅 New time: {when}\n📍 {address}"),
    "n_cancelled": (
        "❌ <b>Запись отменена</b>\n" + DIV + "\n💆 {service}\n\nЧтобы выбрать другое время, нажмите «📅 Записаться» в меню.",
        "❌ <b>Cita cancelada</b>\n" + DIV + "\n💆 {service}\n\nPara elegir otra hora, pulse «📅 Reservar cita» en el menú.",
        "❌ <b>Booking cancelled</b>\n" + DIV + "\n💆 {service}\n\nTo choose another time, tap “📅 Book an appointment” in the menu."),
}
TEXTS = [(k, lab, *DESIGN.get(k, (ru, es, en)), rev) for k, lab, ru, es, en, rev in TEXTS]


LIP_BRANDS = [("Revolax", "160 €"), ("Replengen", "150 €"), ("Stylage", "220 €"), ("Juvederm", "240 €")]


def migrate_lips():
    """Replace the generic 'Увеличение губ' (unconfirmed range) with four brand-specific lip filler prices. Runs once."""
    if db.get_meta("lips_brands"):
        return
    old = db.one("SELECT id, cat_id, sort FROM services WHERE name_ru='Увеличение губ'")
    if old:
        n = len(LIP_BRANDS)
        db.run("UPDATE services SET sort = sort + ? WHERE cat_id=? AND sort > ?", (n, old["cat_id"], old["sort"]))
        for i, (brand, price) in enumerate(LIP_BRANDS, 1):
            db.run("""INSERT INTO services(cat_id, sort, name_ru, name_es, name_en, price, confirmed,
                      desc_ru, desc_es, desc_en, needs_review) VALUES(?,?,?,?,?,?,1,?,?,?,1)""",
                   (old["cat_id"], old["sort"] + i, f"💋 Увеличение губ — {brand}", f"💋 Aumento de labios — {brand}",
                    f"💋 Lip augmentation — {brand}", price, *DESC_FILLER))
        db.run("DELETE FROM services WHERE id=?", (old["id"],))
    db.set_meta("lips_brands", "1")


def run():
    if not db.one("SELECT 1 FROM categories"):
        for i, (grp, names) in enumerate(CATS, 1):
            db.run("INSERT INTO categories(id, grp, sort, name_ru, name_es, name_en) VALUES(?,?,?,?,?,?)",
                   (i, grp, i, *names))
        for n, s in enumerate(SERVICES, 1):
            d = s["desc"] or ("", "", "")
            db.run("""INSERT INTO services(cat_id, sort, name_ru, name_es, name_en, price, price_from, old_price,
                      note_ru, note_es, note_en, confirmed, desc_ru, desc_es, desc_en, needs_review, admin_note)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (s["cat"], n, *s["names"], s["price"], s["frm"], s["old"], *s["note"],
                    1 if (s["ok"] and s["price"]) else 0, *d, 1 if s["desc"] else 0, s["admin"]))
    for i, (key, label, ru, es, en, rev) in enumerate(TEXTS, 1):
        db.run("INSERT OR IGNORE INTO texts(key, label, sort, ru, es, en, needs_review) VALUES(?,?,?,?,?,?,?)",
               (key, label, i, ru, es, en, rev))
    ver = int(db.get_meta("design", "0") or 0)
    if ver < DESIGN_VERSION:
        # v2: restyled texts; v3: Instagram link in contacts. Older DBs get only what they are missing.
        keys = list(DESIGN) if ver < 2 else ["contacts"]
        for key in keys:
            ru, es, en = DESIGN[key]
            db.run("UPDATE texts SET ru=?, es=?, en=? WHERE key=?", (ru, es, en, key))
        db.set_meta("design", str(DESIGN_VERSION))
    migrate_lips()
