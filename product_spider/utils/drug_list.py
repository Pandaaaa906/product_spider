import re

t = """Abacavir
Abiraterone
Acadesine
Acarbose
Acebrophylline
Acebutolol
Aceclofenac
Acetaminophen
Acetylcysteine
Aciclovir
Acipimox
Aclidinium
Acotiamide
Adapalene
Adefovir
Aditoprim
Afatinib
Afloqualone
Agomelatine
Albendazole
Alcaftadine
Alfacalcidol
Alfuzosin
Aliskiren
Allopregnenolone
Allopurinol
Almotriptan
Alogliptin
Alprazolam
Alverine
Alvimopan
Ambrisentan
Ambroxol
Amdinocillin
Amifostine
Amikacin
Aminophylline
Amiodarone
Amisulpride
Amitriptyline
Amlodipine
Amorolfine
Amoxicillin
Amphotericin
Ampicillin
Anabasine
Anastrozole
Androstenol
Anidulafungin
Apixaban
Apremilast
Aprepitant
Arbidol
Argatroban
Argireline
Aripiprazole
Armodafinil
Arotinolol
Artesunate
Articaine
Asenapine
Aspartame
Aspirin
Atazanavir
Atenolol
Atomoxetine
Atorvastatin
Atovaquone
Atracurium
Atropine
Avanafil
Avermectin
Avibactam
Axitinib
Azacitidine
Azathioprine
AZD4547
AZD-9291
Azelastine
Azelnidipine
Azilsartan
Azithromycin
Aztreonam
Bacitracin
Baclofen
Balsalazide
Bazedoxifene
Beclometasone
Beclomethasone
Bedaquiline
Bendamustine
Benexate
Benidipine
Benserazide
Benzamide
Benzenesulfonic
Benzhexol
Benzyl
Benzylpenicillin
Bepotastine
Besifloxacin
Betahistine
Betamethasone
Betaxolol
Bicalutamide
Bifonazole
Bilirubin
Bimatoprost
Biolimus
Biotin
Birabresib
Bisoprolol
Bivalirudin
Blonanserin
Bortezomib
Bosentan
Bosutinib
Bremelanotide
Brexpiprazole
Brimonidine
Brinzolamide
Brivanib
Bromhexine
Bromocriptine
Budesonide
Bupivacaine
Bupropion
Buspirone
Busulfan
Butamirate
Butenafine
Butylhydroxyanisole
Butylphthalide
Cabazitaxel
Caffeine
Calcifediol
Calcipotriol
Calcitriol
Camptothecin
Canagliflozin
Candesartan
Canertinib
Capecitabine
Captopril
Carbamazepine
Carbetocin
Carbuterol
Carfilzomib
Carvedilol
Caspofungin
Cediranib
Cefaclor
Cefadroxil
Cefalexin
Cefalotin
Cefamandole
Cefathiamidine
Cefazedone
Cefazolin
Cefbuperazone
Cefcapene
Cefdinir
Cefditoren
Cefepime
Cefetamet
Cefixime
Cefmenoxime
Cefmetazole
Cefminox
Cefodizime
Cefoperazone
Cefotaxime
Cefotetan
Cefotiam
Cefoxitin
Cefozopran
Cefpirome
Cefpodoxime
Cefprozil
Cefradine
Cefsulodin
Ceftaroline
Ceftazidime
Ceftibuten
Ceftiofur
Ceftizoxime
Ceftriaxone
Cefuroxime
Celecoxib
Cephalexin
Ceritinib
Cetilistat
Cetirizine
Chenodeoxycholic
Chlormezanone
Chlorphenamine
Chlorpheniramine
Chlorpromazine
Chlorthalidone
Cholecalciferol
Cholesterol
Choline
Ciclopirox
Cilastatin
Cilnidipine
Cilostazol
Cimetidine
Cinacalcet
Cinepazide
Cinnarizine
Ciprofloxacin
Citalopram
Clarithromycin
Clavulanic
Clemastine
Clevidipine
Clindamycin
Clobetasol
Clofarabine
Clomiphene
Clomipramine
Clonazepam
Clonidine
Cloperastine
Clopidogrel
Clotrimazole
Cloxacillin
Clozapine
Cobicistat
Colchicine
Conivaptan
Conjugated
Creatine
Crizotinib
Crotamiton
Cyamemazine
Cyanocobalamin
Cyclobenzaprine
Cyclosporin
Cyproheptadine
Cyproterone
Dabigatran
Daclatasvir
Dalbavancin
Dalfopristin
Dapagliflozin
Dapoxetine
Dapsone
Daptomycin
Darifenacin
Darunavir
Dasatinib
Daunorubicin
Decitabine
Deferasirox
Demeclocycline
Dequalinium
Desloratadine
Desonide
Desoximetasone
Desvenlafaxine
Dexamethasone
Dexchlorpheniramine
Dexlansoprazole
Dexmedetomidine
Dexpanthenol
Dextromethorphan
Diacerein
Diazepam
Diazoxide
Diclofenac
Dicloxacillin
Dicyclomine
Didanosine
Diflunisal
Digoxin
Diltiazem
Dimenhydrinate
Diosmin
Diphenhydramine
Diphenoxylate
Dipyridamole
Dirithromycin
Dobutamine
Docetaxel
Dolasetron
Dolutegravir
Domiphen
Domperidone
Donepezil
Dopamine
Doripenem
Dorzolamide
Dovitinib
Doxapram
Doxazosin
Doxepin
Doxofylline
Doxycycline
Doxylamine
Dronedarone
Drospirenone
Droxidopa
Duloxetine
Dutasteride
Dyclonine
Ecabet
Econazole
Edaravone
Edoxaban
Efavirenz
Efinaconazole
Eletriptan
Eltrombopag
Empagliflozin
Emtricitabine
Enalapril
Enoxacin
Enrofloxacin
Entacapone
Entecavir
Enzalutamide
Epinastine
Epinephrine
Epirubicin
Eplerenone
Epothilone
Eprosartan
Erdosteine
Erlotinib
Ertapenem
Erythromycin
EsCitalopram
Esketamine
Esmolol
Esomeprazole
Estazolam
Estradiol
Estriol
Eszopiclone
Ethambutol
Ethinylestradiol
Ethylvanillin
Etodolac
Etomidate
Etoricoxib
Etravirine
Everolimus
Exemestane
Ezetimibe
Famciclovir
Famotidine
Faropenem
Fasudil
Febuxostat
Felodipine
Fenbufen
Fenofibrate
Fentanyl
Fesoterodine
Fexofenadine
Fidaxomicin
Fimasartan
Finasteride
Fingolimod
Flomoxef
Flucloxacillin
Fluconazole
Fludarabine
Flumazenil
Flumetasone
Flunarizine
Flunisolide
Fluorometholone
Fluorouracil
Fluoxetine
Flupentixol
Fluphenazine
Flupirtine
Flurbiprofen
Fluticasone
Fluvastatin
Fluvoxamine
Folic
Formoterol
Fosaprepitant
Fosfomycin
Fosinopril
Fudosteine
Fulvestrant
Furosemide
Fusidic
Gabapentin
Galanthamine
Gamithromycin
Ganciclovir
Gatifloxacin
Gefitinib
Geldanamycin
Gemcitabine
Gentamicin
Gimeracil
Glibenclamide
Gliclazide
Glimepiride
Glipizide
Glucosamine
Glutathione
Glycopyrrolate
Glycopyrronium
Glycyrrhetinic
Goserelin
Granisetron
Guaifenesin
Guanfacine
Halometasone
Haloperidol
Homotaurine
Hyaluronate
Hydralazine
Hydrochlorothiazide
Hydrocortisone
Hydroxychloroquine
Hydroxyzine
Ibrutinib
Ibuprofen
Idarubicin
Iguratimod
Ilaprazole
Iloperidone
Imatinib
Imidafenacin
Imipenem
Imipramine
Indacaterol
Indapamide
Indisetron
Indobufen
Indometacin
Intedanib
Iodixanol
Iohexol
Iomeprol
Iopamidol
Iopromide
Ipragliflozin
Ipratropium
Ipriflavone
Irbesartan
Irinotecan
Isavuconazole
Isoconazole
Isoniazid
Isonicotinic
Istradefylline
Itopride
Itraconazole
Ivabradine
Ixabepilone
Ixazomib
Kanamycin
Ketoconazole
Ketoprofen
Ketorolac
Kojic
Lacidipine
Lacosamide
Lafutidine
Lamivudine
Lamotrigine
Lansoprazole
Lapatinib
Latamoxef
Latanoprost
LCZ
Lecithin
Leflunomide
Lenalidomide
Lenvatinib
Lercanidipine
Lesinurad
Letrozole
Leuprorelin
Levetiracetam
Levocarnitine
Levocetirizine
Levocloperastine
Levodopa
Levofloxacin
Levofolinate
Levonorgestrel
Levosimendan
Levothyroxine
Lidocaine
Linagliptin
Lincomycin
Linezolid
Lipoic
Lipopeptide
Liranaftate
Lisinopril
Lobeline
Loperamide
Lopinavir
Loratadine
Lorazepam
Lorcaserin
Losartan
Loteprednol
Lovastatin
Loxoprofen
Lubiprostone
Lurasidone
Mabuterol
Macitentan
Mafenide
Marbofloxacin
Matrixyl
Mebeverine
Meclizine
Medroxyprogesterone
Megestrol
Melanotan
Melitracen
Meloxicam
Memantine
Mepivacaine
Meptazinol
Meropenem
Mesalamine
Mesalazine
Mesna
Metformin
Methenamine
Methionine
Methotrexate
Methyldopa
Methylergometrinine
Methylnaltrexone
Methylprednisolone
Metoclopramide
Metoprolol
Metronidazole
Mexiletine
Mezlocillin
Mianserin
Micafungin
Miconazole
Midazolam
Mifepristone
Miglitol
Milbemycin
Mildronate
Milnacipran
Milrinone
Minocycline
Minodronic
Minoxidil
Mirabegron
Mirtazapine
Misoprostol
Mitiglinide
Mitomycin
Mitoxantrone
Mivacurium
Mizoribine
Moclobemide
Modafinil
Mometasone
Montelukast
Morroniside
Mosapride
Motesanib
Moxifloxacin
Mupirocin
Mycophenolate
Nafamostat
Naftopidil
Nalfurafine
Nalmefene
Naloxone
Naltrexone
Naphazoline
Naproxen
Nateglinide
Nebivolol
Neomycin
Nepafenac
Neratinib
Netupitant
Nevirapine
Nicardipine
Nicorandil
Nicotinic
Nifedipine
Nifuratel
Nikethamide
Nilotinib
Nilvadipine
Nimesulide
Nimodipine
Nintedanib
Nisoldipine
Nitazoxanide
Nitrendipine
Nizatidine
Norelgestromin
Norepinephrine
Norethindrone
Norfloxacin
Novobiocin
Nysfungin
Nystatin
Obeticholic
Octreotide
Ofloxacin
Olanzapine
Olaparib
Olmesartan
Olodaterol
Olopatadine
Olsalazine
Omarigliptin
Omeprazole
Ondansetron
Orlistat
Ornidazole
Oseltamivir
Ospemifene
Others
Otilonium
Oxaprozin
Oxcarbazepine
Oxiracetam
Oxybuprocaine
Oxybutynin
Oxycodone
Oxymetazoline
Ozagrel
Paclitaxel
Palbociclib
Paliperidone
Palonosetron
Pangamic
Pantoprazole
Parecoxib
Paricalcitol
Paroxetine
Pazopanib
Peforelin
Pemetrexed
Penehyclidine
Pentostatin
Pentoxifylline
Peramivir
Pericyazine
Perindopril
Perphenazine
Phenformin
Phenobarbital
Phenylephrine
Phenytoin
Picosulfate
Pidotimod
Pimavanserin
Pimecrolimus
Pioglitazone
Piperacillin
Piracetam
Piroxicam
Pitavastatin
Pixantrone
Plerixafor
Pneumocandin
Polaprezinc
Pomalidomide
Posaconazole
Potassium
Pramipexole
Pranlukast
Pranoprofen
Prasterone
Prasugrel
Pravastatin
Prazosin
Prednisolone
Pregabalin
Prilocaine
Pristinamycin
Procaterol
Prochlorperazine
Progesterone
Proguanil
Promethazine
Propacetamol
Propafenone
Propiverine
Propofol
Propranolol
Propylthiouracil
Prucalopride
Pyrazinamide
Pyridoxine
Quetiapine
Quinapril
Quinupristin
Rabeprazole
Racecadotril
Raloxifene
Raltitrexed
Ramipril
Ramosetron
Ranitidine
Ranolazine
Rapamycin
Rasagiline
Rebamipide
Rebeccamycin
Reboxetine
Regadenoson
Regorafenib
Repaglinide
Reserpine
Retigabine
Revaprazan
Ribavirin
Riboflavin
Rifampicin
Rifapentine
Rifaximin
Rilpivirine
Riociguat
Risedronate
Risperidone
Ritonavir
Rivaroxaban
Rivastigmine
Rizatriptan
Rocuronium
Roflumilast
Rolapitant
Ropinirole
Ropivacaine
Rosuvastatin
Rotigotine
Roxatidine
Roxithromycin
Rupatadine
Safinamide
Salbutamol
Salicylic
Salmeterol
Saxagliptin
Scopolamine
Selegiline
Selexipag
Seproxetine
Sertaconazole
Sertindole
Sertraline
Sibutramine
Sildenafil
Silodosin
Simvastatin
Sitafloxacin
Sitagliptin
Aminosalicylate
Sofosbuvir
Solifenacin
Sorafenib
Sotrastaurin
Spironolactone
Stanolone
Stavudine
Sufentanil
Sugammadex
Sulbactam
Sulfadimethoxine
Sulfamethoxazole
Sulfasalazine
Sulpiride
Sultamicillin
Sumatriptan
Sunitinib
Suvorexant
Synephrine
Tacrolimus
Tadalafil
Tamoxifen
Tamsulosin
Tandospirone
Tazobactam
Tebipenem
Tedizolid
Teicoplanin
Telmisartan
Temozolomide
Temsirolimus
Teneligliptin
Tenofovir
Terazosin
Terbinafine
Terbutaline
Terfenadine
Tertatolol
Tetracaine
Tetroxoprim
Theophylline
Thiamine
Thioctic
Thioridazine
Thymalfasin
Ticagrelor
Ticarcillin
Tigecycline
Timolol
Tinidazole
Tiopronin
Tiotropium
Tipiracil
Tirofiban
Tizanidine
Tocopherol
Tofacitinib
Tolmetin
Tolnaftate
Tolterodine
Tolvaptan
Topiramate
Topiroxostat
Topotecan
Torasemide
Toremifene
Tosufloxacin
Tramadol
Trandolapril
Tranexamic
Travoprost
Trazodone
Trelagliptin
Tretinoin
Triamcinolone
Triamterene
Triclabendazole
Trimebutine
Trimetazidine
Trimethoprim
Triptorelin
Tropisetron
Tryptophan
Ubenimex
Ubidecarenone
Ulipristal
Umeclidinium
Urapidil
Ursodeoxycholic
Valaciclovir
Valdecoxib
Valganciclovir
Valproate
Valsartan
Vancomycin
Vandetanib
Vardenafil
Varenicline
Vecuronium
Venlafaxine
Verapamil
Vigabatrin
Vilanterol
Vilazodone
Vildagliptin
Vincamine
Vinpocetine
Vitamin
Voglibose
Vonoprazan
Vorapaxar
Voriconazole
Vortioxetine
Warfarin
Xylometazoline
Zeaxanthin
Zidovudine
Zilpaterol
Ziprasidone
Zofenopril
Zolmitriptan
Zolpidem
Zonisamide
Zopiclone
Zotarolimus"""
# 注意API名称不要有空格
l_parent = t.split('\n')
raw_pattern = r"\b" + r'\b|\b'.join(l_parent) + r"\b|.+(?=\s+USP)|.+(?=\s+EP)|.+(?=\s+Imp)|.+(?=-)"
drug_pattern = re.compile(r'|'.join(l_parent) + r"|.+(?= USP )|.+(?= EP )|.+(?= Imp)|.+(?=[- ]d\d+)",
                          re.IGNORECASE)