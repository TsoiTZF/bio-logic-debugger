"""
水稻核心知识库（Oryza sativa）- 更新版

基于权威科学文献和标准更新的数据，包括：
- IRRI（国际水稻研究所）品质评价标准
- 中国国家标准 GB/T 17891《优质稻谷》
- GWAS 和 QTL 研究的性状关联数据
- 最新的水稻育种研究进展

所有数据均附有可靠来源引用。
"""
from bio_logic_debugger.core.domain import (
    AntiPattern,
    BiologicalConstraint,
    ConstraintScope,
    ConstraintSeverity,
    CorrelationEvidence,
    CorrelationType,
    EvidenceLevel,
    FailedApproach,
    Trait,
    TraitCorrelation,
)


# ==============================================================
# 性状定义
# ==============================================================

TRAITS = [
    # ---- 产量性状 ----
    Trait("rice_yield_per_plant", "单株产量", "单株所结稻谷的总重量", "产量", "g", (10.0, 80.0), tags=["产量", "核心"]),
    Trait("rice_yield_per_ha", "亩产", "每亩产量", "产量", "kg", (300.0, 1200.0), tags=["产量", "核心"]),
    Trait("rice_panicle_number", "穗数", "每株有效穗数", "产量", "穗/株", (8.0, 25.0), tags=["产量", "株型"]),
    Trait("rice_grain_per_panicle", "每穗粒数", "每穗的结实粒数", "产量", "粒/穗", (80.0, 350.0), tags=["产量"]),
    Trait("rice_1000_grain_weight", "千粒重", "一千粒饱满谷粒的重量", "产量", "g", (18.0, 35.0), tags=["产量", "粒型"]),
    Trait("rice_harvest_index", "收获指数", "经济产量与生物产量的比值", "产量", "", (0.30, 0.60), tags=["产量", "株型"]),
    Trait("rice_biomass", "生物产量", "单位面积地上部干物质总重", "产量", "t/ha", (8.0, 20.0), tags=["产量"]),
    Trait("rice_spikelet_fertility", "结实率", "实粒数占总粒数的百分比", "产量", "%", (60.0, 95.0), tags=["产量"]),

    # ---- 株型性状 ----
    Trait("rice_plant_height", "株高", "从地面到穗顶的高度", "株型", "cm", (60.0, 150.0), tags=["株型"]),
    Trait("rice_tiller_number", "分蘖数", "单株有效分蘖数量", "株型", "个/株", (5.0, 20.0), tags=["株型", "产量"]),
    Trait("rice_culm_strength", "茎秆强度", "茎秆抗折断能力", "株型", "N", (5.0, 30.0), tags=["株型", "抗逆"]),
    Trait("rice_leaf_angle", "叶角", "叶片与茎秆的夹角", "株型", "度", (10.0, 80.0), tags=["株型", "光合"]),
    Trait("rice_flag_leaf_length", "旗叶长度", "最上部叶片的长度", "株型", "cm", (15.0, 45.0), tags=["株型"]),

    # ---- 品质性状 ----
    Trait("rice_grain_length", "粒长", "谷粒长度", "品质", "mm", (4.0, 9.0), tags=["品质", "粒型"]),
    Trait("rice_grain_width", "粒宽", "谷粒宽度", "品质", "mm", (2.0, 4.0), tags=["品质", "粒型"]),
    Trait("rice_length_width_ratio", "长宽比", "粒长与粒宽的比值", "品质", "", (2.0, 4.5), tags=["品质", "粒型"]),
    Trait("rice_amylose_content", "直链淀粉含量", "稻米直链淀粉含量，影响食味", "品质", "%", (0.0, 33.0), tags=["品质", "食味"]),
    Trait("rice_gel_consistency", "胶稠度", "稻米胶稠度，影响食味口感", "品质", "mm", (26.0, 100.0), tags=["品质", "食味"]),
    Trait("rice_protein_content", "蛋白质含量", "稻米蛋白质含量", "品质", "%", (5.0, 15.0), tags=["品质", "营养"]),
    Trait("rice_chalkiness", "垩白度", "垩白粒占总粒数的百分比", "品质", "%", (0.0, 40.0), tags=["品质", "外观"]),
    Trait("rice_head_rice_recovery", "整精米率", "完整精米占糙米的百分比", "品质", "%", (40.0, 75.0), tags=["品质", "碾磨"]),
    Trait("rice_alkali_spreading_value", "碱消值", "淀粉糊化温度指标", "品质", "级", (1.0, 7.0), tags=["品质", "食味"]),
    Trait("rice_aroma", "香味", "稻米香气物质含量", "品质", "", (0.0, 1.0), tags=["品质", "食味"]),

    # ---- 抗病性状 ----
    Trait("rice_blast_resistance", "稻瘟病抗性", "对稻瘟病的抗性等级", "抗病", "级", (1.0, 9.0), tags=["抗病", "核心"]),
    Trait("rice_bacterial_blight_res", "白叶枯病抗性", "对白叶枯病的抗性等级", "抗病", "级", (1.0, 9.0), tags=["抗病"]),
    Trait("rice_sheath_blight_res", "纹枯病抗性", "对纹枯病的抗性等级", "抗病", "级", (1.0, 9.0), tags=["抗病"]),
    Trait("rice_false_smut_res", "稻曲病抗性", "对稻曲病的抗性等级", "抗病", "级", (1.0, 9.0), tags=["抗病"]),

    # ---- 抗逆性状 ----
    Trait("rice_lodging_resistance", "抗倒伏性", "茎秆抗倒伏能力", "抗逆", "级", (1.0, 9.0), tags=["抗逆", "株型"]),
    Trait("rice_drought_tolerance", "耐旱性", "干旱胁迫下的存活和产量保持能力", "抗逆", "级", (1.0, 9.0), tags=["抗逆"]),
    Trait("rice_cold_tolerance", "耐冷性", "低温胁迫下的生长和结实能力", "抗逆", "级", (1.0, 9.0), tags=["抗逆"]),
    Trait("rice_heat_tolerance", "耐热性", "高温胁迫下的结实能力", "抗逆", "级", (1.0, 9.0), tags=["抗逆"]),
    Trait("rice_salt_tolerance", "耐盐性", "盐胁迫下的生长和产量保持能力", "抗逆", "级", (1.0, 9.0), tags=["抗逆"]),
    Trait("rice_submergence_tolerance", "耐淹性", "淹水胁迫下的存活能力", "抗逆", "级", (1.0, 9.0), tags=["抗逆"]),

    # ---- 生育期性状 ----
    Trait("rice_heading_days", "抽穗天数", "从播种到抽穗的天数", "生育期", "天", (60.0, 180.0), tags=["生育期"]),
    Trait("rice_grain_filling_period", "灌浆期", "从抽穗到成熟的天数", "生育期", "天", (20.0, 55.0), tags=["生育期"]),
    Trait("rice_growth_duration", "全生育期", "从播种到成熟的总天数", "生育期", "天", (90.0, 210.0), tags=["生育期"]),

    # ---- 光合与生理性状 ----
    Trait("rice_photosynthetic_rate", "光合速率", "单位叶面积的光合效率", "生理", "μmol/m²/s", (10.0, 30.0), tags=["生理", "光合"]),
    Trait("rice_spad_value", "SPAD值", "叶绿素含量指标", "生理", "", (30.0, 50.0), tags=["生理", "光合"]),
    Trait("rice_root_depth", "根系深度", "根系分布的深度", "生理", "cm", (10.0, 50.0), tags=["生理", "根系"]),
    Trait("rice_nitrogen_use_efficiency", "氮肥利用率", "单位氮肥投入的产量产出", "生理", "kg/kg", (10.0, 50.0), tags=["生理", "营养"]),
]

# ==============================================================
# 性状关联
# ==============================================================

CORRELATIONS = [
    # ---- 产量内部的拮抗 ----
    TraitCorrelation(
        "rice_panicle_number", "rice_grain_per_panicle",
        CorrelationType.NEGATIVE, -0.45,
        confidence=0.85,
        mechanism="光合产物分配竞争：穗数增加导致每穗可分配的光合产物减少，单穗粒数随之下降。这是源-库关系的经典表现。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "Yoshida, 1981, Fundamentals of Rice Crop Science", "经典教材中的源-库理论", year=1981),
            CorrelationEvidence(EvidenceLevel.STRONG, "Fageria et al., 2006, Journal of Plant Nutrition", "产量构成因素的通径分析，穗数与每穗粒数负相关 r=-0.42", year=2006),
            CorrelationEvidence(EvidenceLevel.STRONG, "中国水稻研究所多年田间数据", "长江中下游稻区多年数据统计", year=2019),
        ],
        antagonistic_threshold=0.3,
    ),
    TraitCorrelation(
        "rice_grain_per_panicle", "rice_1000_grain_weight",
        CorrelationType.NEGATIVE, -0.30,
        confidence=0.70,
        mechanism="籽粒数量增加后，单个籽粒的灌浆物质供应不足，导致粒重下降。尤其在灌浆期光温条件受限时更为明显。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "Peng et al., 2008, Rice yield potential", "IRRI 长期育种数据分析", year=2008),
            CorrelationEvidence(EvidenceLevel.STRONG, "Kumar et al., 2014, Indian Journal of Genetics", "产量构成因素相关分析，r=-0.28", year=2014),
        ],
        antagonistic_threshold=0.25,
    ),
    TraitCorrelation(
        "rice_panicle_number", "rice_1000_grain_weight",
        CorrelationType.NEGATIVE, -0.25,
        confidence=0.65,
        mechanism="穗数过多导致群体郁闭，影响灌浆期光合产物积累，从而降低千粒重。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "Fageria et al., 2006", "穗数与千粒重负相关 r=-0.22", year=2006),
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "中国水稻育种实践", "多穗型品种往往千粒重偏低"),
        ],
        antagonistic_threshold=0.20,
    ),
    TraitCorrelation(
        "rice_yield_per_plant", "rice_grain_length",
        CorrelationType.TRADE_OFF, -0.35,
        confidence=0.75,
        mechanism="长粒型品种通常库容有限，单位面积粒数少于短粒品种，从而限制产量潜力。粒型改良往往以产量为代价。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "中国优质稻育种实践", "多年优质稻育种总结"),
            CorrelationEvidence(EvidenceLevel.STRONG, "Fan et al., 2006, GS3 gene cloning", "GS3 基因对粒长和粒重的多效性", year=2006),
        ],
        antagonistic_threshold=0.3,
    ),

    # ---- 品质-产量权衡 ----
    TraitCorrelation(
        "rice_yield_per_plant", "rice_amylose_content",
        CorrelationType.TRADE_OFF, -0.25,
        confidence=0.60,
        mechanism="高产栽培往往伴随高氮肥投入，影响直链淀粉合成。二者之间的平衡受栽培措施和品种遗传背景共同影响。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "部分育种报告", "非严格一致的关联，因品种而异"),
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "Li et al., 2023, Theoretical and Applied Genetics", "产量与品质权衡的综述", year=2023),
        ],
        antagonistic_threshold=0.25,
    ),
    TraitCorrelation(
        "rice_yield_per_ha", "rice_chalkiness",
        CorrelationType.POSITIVE, 0.30,
        confidence=0.70,
        mechanism="高产品种往往灌浆不充分，导致垩白度增加。垩白度是外观品质的重要指标。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "中国水稻研究所品质分析", "高产品种垩白度普遍偏高"),
            CorrelationEvidence(EvidenceLevel.STRONG, "Chalk5 基因研究", "垩白形成与灌浆物质分配相关"),
        ],
    ),
    TraitCorrelation(
        "rice_1000_grain_weight", "rice_chalkiness",
        CorrelationType.POSITIVE, 0.40,
        confidence=0.75,
        mechanism="千粒重增加往往伴随籽粒增大，灌浆物质向籽粒中心扩散不充分，导致腹白和心白增加。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "水稻品质遗传研究", "粒型与垩白的正相关关系"),
        ],
    ),
    TraitCorrelation(
        "rice_grain_length", "rice_1000_grain_weight",
        CorrelationType.POSITIVE, 0.55,
        confidence=0.85,
        mechanism="粒长和千粒重由共同的粒型基因（如 GS3, GW5）控制，粒长增加通常伴随着千粒重的提升。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "Fan et al., 2006, GS3 gene cloning", "GS3 基因对粒长和粒重的多效性", year=2006),
        ],
    ),
    TraitCorrelation(
        "rice_grain_width", "rice_1000_grain_weight",
        CorrelationType.POSITIVE, 0.60,
        confidence=0.85,
        mechanism="粒宽是千粒重的关键决定因子之一。粒宽基因 GW2, GW5 的变异直接影响千粒重。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "Song et al., 2007, GW2 gene", "GW2 基因对粒宽和粒重的正效应", year=2007),
        ],
    ),

    # ---- 品质内部关联 ----
    TraitCorrelation(
        "rice_amylose_content", "rice_gel_consistency",
        CorrelationType.NEGATIVE, -0.65,
        confidence=0.85,
        mechanism="直链淀粉含量越高，胶稠度越短（米饭越硬）。这是稻米食味品质的核心化学基础。AC 过高（>25%）导致米饭硬、冷后回生；过低（<2%）则米饭过黏。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "IRRI 稻米品质评价标准", "国际水稻研究所标准"),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "Juliano, 1971, Cereal Science Today", "稻米品质分析方法学", year=1971),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "中国水稻研究所品质分析", "多年品质数据累积"),
        ],
    ),
    TraitCorrelation(
        "rice_amylose_content", "rice_alkali_spreading_value",
        CorrelationType.NEGATIVE, -0.40,
        confidence=0.70,
        mechanism="直链淀粉含量高的品种通常糊化温度也高（碱消值低），蒸煮时间长。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "IRRI 品质评价体系", "直链淀粉与糊化温度的负相关"),
        ],
    ),
    TraitCorrelation(
        "rice_protein_content", "rice_amylose_content",
        CorrelationType.CURVILINEAR, 0.0,
        confidence=0.50,
        mechanism="蛋白质含量与直链淀粉含量的关系受施氮量调控：低氮条件下二者正相关，高氮条件下关系复杂化，且蛋白质含量升高会掩盖直链淀粉对食味的影响。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "综合文献调研", "关系不恒定，受环境条件影响大"),
        ],
    ),
    TraitCorrelation(
        "rice_chalkiness", "rice_head_rice_recovery",
        CorrelationType.NEGATIVE, -0.55,
        confidence=0.80,
        mechanism="垩白度高的籽粒内部结构疏松，碾磨时容易碎裂，导致整精米率下降。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "稻米碾磨品质研究", "垩白与整精米率的负相关关系"),
            CorrelationEvidence(EvidenceLevel.STRONG, "中国优质稻谷标准 GB/T 17891", "垩白度和整精米率均为重要品质指标"),
        ],
    ),
    TraitCorrelation(
        "rice_grain_length", "rice_head_rice_recovery",
        CorrelationType.NEGATIVE, -0.35,
        confidence=0.65,
        mechanism="过长的籽粒在碾磨过程中更容易断裂，尤其是当粒长超过 8mm 时，整精米率显著下降。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "稻米碾磨品质研究", "粒长与整精米率的负相关"),
        ],
    ),

    # ---- 株型-产量-抗逆 ----
    TraitCorrelation(
        "rice_plant_height", "rice_lodging_resistance",
        CorrelationType.NEGATIVE, -0.55,
        confidence=0.85,
        mechanism="株高越高，重心升高，茎秆承受的弯矩增大，抗倒伏能力下降。半矮秆基因（sd1）的利用是绿色革命的核心。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "绿色革命经典理论", "sd1 半矮秆基因的广泛应用"),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "Khush, 1999, Green Revolution", "水稻绿色革命的回顾", year=1999),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "sd1 基因功能研究", "sd1 降低株高 20-30%，显著提高抗倒伏性"),
        ],
        antagonistic_threshold=0.4,
    ),
    TraitCorrelation(
        "rice_plant_height", "rice_yield_per_plant",
        CorrelationType.CURVILINEAR, 0.0,
        confidence=0.75,
        mechanism="株高与产量的关系呈倒U型：过矮（<70cm）生物量不足限制产量，过高（>130cm）则因倒伏风险增加和收获指数下降而减产。最佳株高通常在 90-110cm 之间。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "IRRI 株型育种理论", "动态株型概念"),
            CorrelationEvidence(EvidenceLevel.STRONG, "收获指数研究", "现代半矮秆品种收获指数 0.50-0.55，传统高秆品种 0.30-0.40"),
        ],
    ),
    TraitCorrelation(
        "rice_plant_height", "rice_harvest_index",
        CorrelationType.NEGATIVE, -0.60,
        confidence=0.85,
        mechanism="株高越矮，分配到茎秆的生物量越少，收获指数越高。这是绿色革命提高产量的核心机制之一。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "绿色革命理论", "矮秆品种收获指数显著提高"),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "收获指数理论", "收获指数的生物学上限约 0.60"),
        ],
        antagonistic_threshold=0.4,
    ),
    TraitCorrelation(
        "rice_tiller_number", "rice_panicle_number",
        CorrelationType.POSITIVE, 0.75,
        confidence=0.90,
        mechanism="有效分蘖数直接决定穗数。分蘖是水稻产量形成的基础。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "作物栽培学通论", "分蘖与穗数的正相关关系"),
        ],
    ),
    TraitCorrelation(
        "rice_culm_strength", "rice_lodging_resistance",
        CorrelationType.POSITIVE, 0.65,
        confidence=0.80,
        mechanism="茎秆强度是抗倒伏性的物质基础。茎秆机械组织发达、细胞壁厚的品种抗倒伏能力强。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "水稻茎秆力学研究", "茎秆强度与抗倒伏性的正相关"),
        ],
    ),

    # ---- 抗病-产量 ----
    TraitCorrelation(
        "rice_blast_resistance", "rice_yield_per_plant",
        CorrelationType.TRADE_OFF, -0.20,
        confidence=0.40,
        mechanism="部分广谱抗稻瘟病基因（如 Pi-ta, Pi-b）的导入可能带来微小的产量代价，但这一关联因遗传背景不同而差异很大。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "部分育种实践报告", "产量代价因基因和背景而异"),
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "Khanna et al., 2015", "抗病基因堆叠的产量代价研究", year=2015),
        ],
        antagonistic_threshold=0.2,
    ),
    TraitCorrelation(
        "rice_blast_resistance", "rice_bacterial_blight_res",
        CorrelationType.POSITIVE, 0.30,
        confidence=0.55,
        mechanism="部分抗病基因可能存在连锁或一因多效，导致对不同病害的抗性同时出现。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "抗病基因定位研究", "部分抗病基因簇的存在"),
        ],
    ),

    # ---- 生育期相关 ----
    TraitCorrelation(
        "rice_heading_days", "rice_grain_filling_period",
        CorrelationType.POSITIVE, 0.40,
        confidence=0.75,
        mechanism="早熟品种通常灌浆期也较短，限制了光合产物积累时间，进而影响粒重和品质。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "中国水稻所生育期研究", "早、中、晚稻品种数据分析"),
            CorrelationEvidence(EvidenceLevel.STRONG, "光周期基因研究", "Hd1、Ghd7 等基因同时影响抽穗期和灌浆期"),
        ],
    ),
    TraitCorrelation(
        "rice_heading_days", "rice_yield_per_plant",
        CorrelationType.POSITIVE, 0.50,
        confidence=0.80,
        mechanism="生育期越长，光合产物积累期越长，产量潜力越大。但过长则受茬口和季节限制。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "作物生理学通论", "生育期与产量潜力的基本关系"),
            CorrelationEvidence(EvidenceLevel.STRONG, "Ghd7 基因研究", "Ghd7 功能性等位基因延迟抽穗 10-20 天，增加产量潜力", year=2008),
        ],
    ),
    TraitCorrelation(
        "rice_growth_duration", "rice_biomass",
        CorrelationType.POSITIVE, 0.55,
        confidence=0.80,
        mechanism="全生育期越长，光合作用时间越长，生物产量越高。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "作物生理学研究", "生育期与生物产量的正相关"),
        ],
    ),

    # ---- 耐旱性相关 ----
    TraitCorrelation(
        "rice_drought_tolerance", "rice_yield_per_plant",
        CorrelationType.TRADE_OFF, -0.25,
        confidence=0.55,
        mechanism="耐旱性选育往往伴随产量潜力的损失。在水分充足条件下，耐旱品种产量通常低于高产品种。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "IRRI 耐旱育种研究", "耐旱性与产量的权衡关系"),
            CorrelationEvidence(EvidenceLevel.STRONG, "qDTY 位点研究", "耐旱 QTL 的产量代价", year=2010),
        ],
        antagonistic_threshold=0.2,
    ),
    TraitCorrelation(
        "rice_root_depth", "rice_drought_tolerance",
        CorrelationType.POSITIVE, 0.60,
        confidence=0.75,
        mechanism="深根系能够利用深层土壤水分，提高干旱胁迫下的水分获取能力。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "DRO1 基因研究", "深根基因 DRO1 提高耐旱性"),
            CorrelationEvidence(EvidenceLevel.STRONG, "IRRI 根系研究", "根系深度与耐旱性的正相关"),
        ],
    ),

    # ---- 光合相关 ----
    TraitCorrelation(
        "rice_spad_value", "rice_photosynthetic_rate",
        CorrelationType.POSITIVE, 0.45,
        confidence=0.65,
        mechanism="SPAD 值反映叶绿素含量，叶绿素含量高的叶片光合速率通常较高。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "光合作用研究", "叶绿素含量与光合速率的正相关"),
        ],
    ),
    TraitCorrelation(
        "rice_leaf_angle", "rice_photosynthetic_rate",
        CorrelationType.CURVILINEAR, 0.0,
        confidence=0.60,
        mechanism="叶角影响冠层光分布。直立叶（小叶角）有利于光在冠层内均匀分布，提高群体光合效率。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "理想株型理论", "直立叶型提高光能利用效率"),
        ],
    ),

    # ---- 氮肥利用率相关 ----
    TraitCorrelation(
        "rice_nitrogen_use_efficiency", "rice_yield_per_plant",
        CorrelationType.POSITIVE, 0.40,
        confidence=0.60,
        mechanism="氮肥利用率高的品种在相同氮肥投入下能获得更高产量。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "氮肥利用效率研究", "氮效率与产量的正相关"),
        ],
    ),
    TraitCorrelation(
        "rice_nitrogen_use_efficiency", "rice_protein_content",
        CorrelationType.NEGATIVE, -0.30,
        confidence=0.50,
        mechanism="氮肥利用率高的品种往往将更多氮素用于产量形成而非蛋白质积累。",
        evidence=[
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "氮代谢研究", "氮分配与品质的关系"),
        ],
    ),
]


# ==============================================================
# 反模式
# ==============================================================

ANTI_PATTERNS = [
    AntiPattern(
        id="rice_high_yield_low_quality",
        name="高产低质的陷阱",
        description=(
            "追求单一产量指标突破的情况下，品质性状（粒型、食味）往往会系统性下降。"
            "过去三十年中国优质稻育种的经验表明，在不引入特殊种质资源的条件下，"
            "亩产超过 800kg 的品种鲜有达到国标一级优质米的案例。"
        ),
        trigger_traits=["rice_yield_per_ha", "rice_grain_length", "rice_amylose_content"],
        severity=ConstraintSeverity.SEVERE,
        historical_examples=[
            "1990s 湖南高产稻推广：产量突出但米质差，市场接受度低",
            "2000s 部分超级稻品种：产量达标但食味评分偏低，难以形成品牌",
            "部分杂交稻组合：产量优势明显但垩白度高、整精米率低",
        ],
        failed_approaches=[
            FailedApproach(
                "单纯增加穗数追求高产",
                "穗数过多导致籽粒充实度下降，整精米率降低",
                year_range=(1990, 2005),
                reference="中国超级稻育种二十年回顾",
            ),
            FailedApproach(
                "在籼稻背景下导入高产基因不兼顾品质",
                "虽然产量提升 10-15%，但垩白度显著增加，外观品质下降",
                year_range=(2000, 2015),
            ),
            FailedApproach(
                "过度追求大粒型",
                "千粒重增加导致垩白度升高，整精米率下降",
                year_range=(2005, 2020),
                reference="粒型与品质的权衡关系研究",
            ),
        ],
        alternative_directions=[
            "寻找同时控制产量和品质的主效QTL区间，如 GW7/qGL7 同时增加粒长且不影响产量",
            "采用分子标记辅助选择，打破产量-品质的连锁累赘",
            "考虑分步实现：先构建优质基础材料，再叠加产量基因",
            "利用基因编辑技术（CRISPR）精准调控品质基因，减少产量代价",
            "选择垩白度低、整精米率高的亲本作为品质改良基础",
        ],
        mechanism=(
            "产量和品质之间存在共同的碳水化合物分配限制。"
            "高产需要更多的籽粒库容，而优质需要充足的灌浆物质积累。"
            "二者在光合产物分配上构成竞争关系。"
            "此外，高产栽培的高氮投入也会影响淀粉合成和品质形成。"
        ),
        confidence=0.85,
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "中国超级稻育种项目评估报告", "多年超级稻育种项目评估数据", year=2020),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "稻米品质与产量关系的生理学基础", "稻米品质与产量关系的生理学基础研究数据", year=2018),
            CorrelationEvidence(EvidenceLevel.STRONG, "Li et al., 2023, Theoretical and Applied Genetics", "产量与品质权衡的综述", year=2023),
            CorrelationEvidence(EvidenceLevel.STRONG, "Zhou et al., 2023, Nature Communications", "产量与品质协同改良研究", year=2023),
        ],
        species="水稻",
    ),
    AntiPattern(
        id="rice_extreme_grain_type",
        name="极端粒型的代价",
        description=(
            "过度追求特长粒（>8mm）或特宽粒（>3.5mm）往往导致整精米率急剧下降、"
            "垩白度升高、以及灌浆不充实。市场对极端粒型的接受度也有限。"
        ),
        trigger_traits=["rice_grain_length", "rice_grain_width", "rice_1000_grain_weight", "rice_chalkiness"],
        severity=ConstraintSeverity.WARNING,
        historical_examples=[
            "部分长粒籼稻品种：粒长超过 8mm 但整精米率低于 45%",
            "某些泰国香稻衍生系：过度追求细长粒型导致产量潜力受限",
            "部分大粒型品种：千粒重超过 35g 但垩白度超过 15%",
        ],
        failed_approaches=[
            FailedApproach(
                "粒长超过 8.5mm 的选育",
                "籽粒灌浆不充实，整精米率低于 40%，且垩白度超过 10%",
            ),
            FailedApproach(
                "粒宽超过 3.5mm 的选育",
                "虽然千粒重高，但垩白度显著增加，外观品质差",
            ),
        ],
        alternative_directions=[
            "将粒长控制在 7.0-7.5mm，兼顾碾磨品质和外观",
            "粒长和粒宽的协调改良，追求长宽比>3.0 而非绝对长度",
            "优先选择垩白度低、整精米率高的粒型组合",
            "利用 GS3、GW5 等主效基因的优良等位基因进行精准改良",
        ],
        mechanism="籽粒长度超过遗传限制后，胚乳发育过程中背部与腹部的细胞分裂不同步，导致垩白产生。粒宽过大则导致灌浆物质向籽粒中心扩散不充分。",
        confidence=0.75,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "Fan et al., 2006, GS3 gene", "GS3 基因对粒长的调控", year=2006),
            CorrelationEvidence(EvidenceLevel.STRONG, "Song et al., 2007, GW2 gene", "GW2 基因对粒宽的调控", year=2007),
            CorrelationEvidence(EvidenceLevel.STRONG, "稻米碾磨品质研究", "粒型与整精米率的负相关"),
        ],
        species="水稻",
    ),
    AntiPattern(
        id="rice_semi_dwarf_extreme",
        name="过度矮化的产量陷阱",
        description=(
            "sd1 半矮秆基因是绿色革命的基础，但并非越矮越好。"
            "株高低于 70cm 时，生物量不足导致产量潜力严重受限，"
            "且叶片过密影响冠层光合效率。"
        ),
        trigger_traits=["rice_plant_height", "rice_yield_per_plant", "rice_lodging_resistance", "rice_harvest_index"],
        severity=ConstraintSeverity.WARNING,
        historical_examples=[
            "部分育种项目盲目矮化：株高 60-65cm 品系，产量不到正常品种 70%",
            "过度矮化导致生物量不足，收获指数虽高但绝对产量低",
        ],
        failed_approaches=[
            FailedApproach(
                "株高低于 65cm 的选育",
                "生物量严重不足，产量潜力受限",
                year_range=(1980, 2000),
                reference="过度矮化的产量代价研究",
            ),
        ],
        alternative_directions=[
            "理想株高控制在 90-110cm，配合强秆基因提高抗倒伏性",
            "探索理想株型（ideotype）概念：不是简单矮化，而是优化株型结构",
            "利用新的矮秆基因（如 d50）替代 sd1，拓宽遗传基础",
            "结合茎秆强度（culm strength）选择，而非单纯降低株高",
        ],
        mechanism="株高极端降低虽然增强了抗倒伏性，但同时也减少了光合作用器官的总量，限制了生物产量，进而制约经济产量。收获指数的生物学上限约 0.60，无法无限提高。",
        confidence=0.80,
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "绿色革命理论", "sd1 基因的应用与限制"),
            CorrelationEvidence(EvidenceLevel.STRONG, "收获指数理论", "收获指数的生物学上限"),
            CorrelationEvidence(EvidenceLevel.STRONG, "d50 基因研究", "新矮秆基因的探索"),
        ],
        species="水稻",
    ),
    AntiPattern(
        id="rice_precocious_sacrifice",
        name="早熟必低产的经验律",
        description=(
            "生育期每缩短 10 天，产量潜力平均下降约 8-12%。"
            "这是光合产物积累时间缩短的必然结果。"
            "要求在极早熟背景下实现超高产，是已知的育种死胡同。"
        ),
        trigger_traits=["rice_heading_days", "rice_yield_per_plant", "rice_biomass"],
        severity=ConstraintSeverity.SEVERE,
        historical_examples=[
            "东北早熟稻区：生育期 120 天以下品种，产量长期低于中晚熟品种 30%",
            "华南双季稻早稻：生育期紧逼百天，产量潜力天花板明显",
            "部分极早熟品种：生育期 100 天以下，产量仅为正常品种的 60-70%",
        ],
        alternative_directions=[
            "优化灌浆期光合效率而非延长生育期",
            "利用强光效基因（如 C4 途径相关基因）弥补生育期短的不足",
            "考虑温光资源匹配：确保灌浆期处于最佳光温条件下",
            "利用光周期敏感基因（如 Ghd7）优化抽穗期，而非简单缩短生育期",
            "选择灌浆速率高的品种，缩短灌浆期但不降低粒重",
        ],
        mechanism="生育期=光合产物积累时间。在相同的生长速率下，积累时间越长总产量越高。这是作物生理学的基本原理。Ghd7 等基因通过调控抽穗期影响产量潜力。",
        confidence=0.90,
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "作物生理学通论", "生育期与产量的基本关系"),
            CorrelationEvidence(EvidenceLevel.STRONG, "Xue et al., 2008, Nature Genetics", "Ghd7 基因对生育期和产量的调控", year=2008),
            CorrelationEvidence(EvidenceLevel.STRONG, "中国水稻生育期研究", "早中晚稻品种产量差异分析"),
        ],
        species="水稻",
    ),
    AntiPattern(
        id="rice_total_disease_resistance",
        name="全面抗病的性价比陷阱",
        description=(
            "试图同时针对所有主要病害（稻瘟病、白叶枯病、纹枯病、稻曲病等）"
            "达到高抗水平，往往导致抗性基因堆叠过多，引起生长势下降和产量损失。"
            "这就是所谓的「抗性代价」（resistance cost）。"
        ),
        trigger_traits=["rice_blast_resistance", "rice_bacterial_blight_res", "rice_yield_per_plant"],
        severity=ConstraintSeverity.WARNING,
        historical_examples=[
            "IRRI 部分多抗品系：携带 5+ 抗病基因但田间产量缺陷明显",
            "部分基因聚合品系：抗性谱广但生长势弱，产量低于亲本",
        ],
        failed_approaches=[
            FailedApproach(
                "堆叠 5 个以上主效抗病基因",
                "累积性的生长代价导致产量下降 10-15%",
                year_range=(2000, 2020),
                reference="Khanna et al., 2015, 抗病基因堆叠研究",
            ),
        ],
        alternative_directions=[
            "确定目标区域的主控病害，优先保证对主要病害的抗性",
            "利用广谱抗病基因（如 Pik, Xa21）而非堆叠多个小种特异性基因",
            "结合抗病基因和田间管理（预测预警系统），降低抗性压力",
            "利用定量抗性（如 pi21）替代主效 R 基因，降低抗性代价",
            "采用基因编辑技术精准改良抗性，减少连锁累赘",
        ],
        mechanism="每个 R 基因的维持和表达都需要消耗植物的能量和代谢资源。过多抗病基因的堆叠产生累积性的生长代价（fitness cost）。此外，抗性基因导入可能带来连锁累赘。",
        confidence=0.65,
        evidence=[
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "IRRI 部分多抗品系田间数据", "多抗品系产量缺陷观察"),
            CorrelationEvidence(EvidenceLevel.STRONG, "Khanna et al., 2015", "抗病基因堆叠的产量代价", year=2015),
            CorrelationEvidence(EvidenceLevel.STRONG, "Fukuoka et al., 2009", "pi21 定量抗性研究", year=2009),
        ],
        species="水稻",
    ),
    AntiPattern(
        id="rice_drought_yield_tradeoff",
        name="耐旱与高产的两难",
        description=(
            "耐旱性选育往往伴随产量潜力的损失。在水分充足条件下，耐旱品种产量通常低于高产品种 10-20%。"
            "这是由于耐旱机制（如气孔关闭、根系分配增加）与高产机制（如光合效率、籽粒灌浆）存在内在冲突。"
        ),
        trigger_traits=["rice_drought_tolerance", "rice_yield_per_plant", "rice_root_depth"],
        severity=ConstraintSeverity.WARNING,
        historical_examples=[
            "IRRI 耐旱品系：耐旱性好但产量潜力低于高产品种",
            "部分 qDTY 导入系：耐旱性提高但产量代价明显",
            "非洲雨养稻区：耐旱品种产量普遍低于灌溉区品种",
        ],
        failed_approaches=[
            FailedApproach(
                "单纯选择深根系提高耐旱性",
                "根系分配增加导致地上部生物量和产量下降",
                year_range=(2000, 2015),
                reference="DRO1 基因研究",
            ),
            FailedApproach(
                "导入多个耐旱 QTL",
                "累积性的产量代价导致在灌溉条件下产量显著下降",
                year_range=(2005, 2020),
                reference="qDTY 位点研究",
            ),
        ],
        alternative_directions=[
            "根据目标环境的水分条件选择合适的耐旱水平",
            "利用气孔调控基因（如 OsERA1）优化气孔响应，减少产量代价",
            "结合耐旱品种与节水灌溉技术（如 AWD），实现水肥高效",
            "选择灌浆期耐旱的品种，而非全生育期耐旱",
            "利用基因编辑技术精准调控耐旱相关基因",
        ],
        mechanism="耐旱机制与高产机制存在内在冲突。气孔关闭减少水分蒸腾但也降低光合速率；根系分配增加提高水分获取但减少地上部生物量。这是植物资源分配的基本权衡。",
        confidence=0.70,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "IRRI 耐旱育种研究", "耐旱性与产量的权衡"),
            CorrelationEvidence(EvidenceLevel.STRONG, "qDTY 位点研究", "耐旱 QTL 的产量代价"),
            CorrelationEvidence(EvidenceLevel.STRONG, "DRO1 基因研究", "深根基因的产量代价", year=2010),
        ],
        species="水稻",
    ),
    AntiPattern(
        id="rice_chalkiness_quality",
        name="垩白度超标陷阱",
        description=(
            "垩白度是稻米外观品质的核心指标。垩白度超过 10% 的稻米在市场上的接受度显著下降。"
            "垩白形成受遗传和环境双重影响，高温、高氮等栽培条件会加剧垩白发生。"
        ),
        trigger_traits=["rice_chalkiness", "rice_head_rice_recovery", "rice_1000_grain_weight"],
        severity=ConstraintSeverity.WARNING,
        historical_examples=[
            "部分高产品种：垩白度超过 20%，整精米率低于 50%",
            "高温年份稻米：垩白度普遍增加，品质下降",
            "大粒型品种：千粒重高但垩白度超标",
        ],
        failed_approaches=[
            FailedApproach(
                "不关注垩白度的选育",
                "虽然产量达标但品质不达标，市场竞争力差",
                year_range=(1990, 2010),
                reference="中国优质稻育种实践",
            ),
        ],
        alternative_directions=[
            "将垩白度作为品质选育的核心指标，目标 <5%",
            "利用 Chalk5 等基因的优良等位基因降低垩白度",
            "优化栽培管理，避免高温和高氮导致的垩白增加",
            "选择灌浆充分的品种，确保籽粒充实度",
            "结合整精米率选择，确保碾磨品质",
        ],
        mechanism="垩白是由于胚乳细胞中淀粉粒排列疏松、空气间隙增大所致。灌浆不充分、高温胁迫、淀粉合成相关基因变异等都是垩白形成的原因。",
        confidence=0.80,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "Chalk5 基因研究", "垩白形成的分子机制"),
            CorrelationEvidence(EvidenceLevel.STRONG, "中国优质稻谷标准 GB/T 17891", "垩白度的品质分级标准"),
            CorrelationEvidence(EvidenceLevel.STRONG, "稻米品质遗传研究", "垩白度的遗传和环境效应"),
        ],
        species="水稻",
    ),
]


# ==============================================================
# 约束规则
# ==============================================================

CONSTRAINTS = [
    BiologicalConstraint(
        id="rice_not_both_tall_and_lodging_free",
        name="株高与抗倒伏的不可兼得",
        description="高度超过 120cm 的品种几乎不可能具有高抗倒伏性（>7级）。",
        severity=ConstraintSeverity.FATAL,
        scope=ConstraintScope.SPECIES,
        species="水稻",
        condition_expr="$rice_plant_height > 120 AND $rice_lodging_resistance >= 7",
        consequence="超出茎秆力学的物理极限，倒伏风险极高。倒伏可导致产量损失 25-80%。",
        confidence=0.90,
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "作物倒伏力学研究", "茎秆受力分析"),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "sd1 基因研究", "半矮秆基因提高抗倒伏性的机制"),
            CorrelationEvidence(EvidenceLevel.STRONG, "Khush, 1999, Green Revolution", "绿色革命的核心：矮秆抗倒伏", year=1999),
        ],
    ),
    BiologicalConstraint(
        id="rice_amylose_gel_mismatch",
        name="直链淀粉与胶稠度的匹配约束",
        description="高直链淀粉（>25%）品种胶稠度不可能达到软胶稠度（>80mm），反之亦然。",
        severity=ConstraintSeverity.FATAL,
        scope=ConstraintScope.SPECIES,
        species="水稻",
        condition_expr="$rice_amylose_content > 25 AND $rice_gel_consistency > 80",
        consequence="违背稻米淀粉理化性质的基本规律。",
        confidence=0.95,
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "稻米品质化学原理", "稻米直链淀粉与胶稠度的理化关系"),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "Juliano, 1971, Cereal Science Today", "稻米品质分析方法学", year=1971),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "IRRI 品质评价标准", "直链淀粉与胶稠度的对应关系"),
        ],
    ),
    BiologicalConstraint(
        id="rice_extreme_precocity",
        name="极端早熟的生育期下限",
        description="籼稻抽穗天数低于 65 天或粳稻低于 70 天时，基本营养生长期不足，无法形成足够的分蘖和叶片。",
        severity=ConstraintSeverity.FATAL,
        scope=ConstraintScope.SUBSPECIES,
        species="水稻",
        condition_expr="$rice_heading_days < 65",
        consequence="基本营养体不足，产量没有保障。分蘖数和叶面积指数无法达到有效水平。",
        confidence=0.90,
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "作物栽培学通论", "水稻基本营养生长期需求"),
            CorrelationEvidence(EvidenceLevel.STRONG, "光周期基因研究", "Hd1、Ghd7 等基因对生育期的调控"),
        ],
        tags=["生育期", "临界值"],
    ),
    BiologicalConstraint(
        id="rice_harvest_index_ceiling",
        name="收获指数的生物学上限",
        description="水稻收获指数不可能超过 0.65。超过此值意味着茎鞘和叶片生物量不足，无法支撑正常的光合作用和物质转运。",
        severity=ConstraintSeverity.FATAL,
        scope=ConstraintScope.SPECIES,
        species="水稻",
        condition_expr="$rice_harvest_index > 0.65",
        consequence="茎鞘和叶片生物量不足，光合能力受限，产量形成缺乏物质基础。",
        confidence=0.90,
        evidence=[
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "收获指数理论", "收获指数的生物学上限研究"),
            CorrelationEvidence(EvidenceLevel.CONFIRMED, "绿色革命理论", "现代品种收获指数 0.50-0.55"),
            CorrelationEvidence(EvidenceLevel.STRONG, "作物生理学研究", "收获指数与生物量分配的关系"),
        ],
        tags=["收获指数", "理论上限"],
    ),
    BiologicalConstraint(
        id="rice_chalkiness_head_rice",
        name="垩白度与整精米率的匹配约束",
        description="垩白度超过 30% 的品种，整精米率几乎不可能达到 60% 以上。",
        severity=ConstraintSeverity.SEVERE,
        scope=ConstraintScope.SPECIES,
        species="水稻",
        condition_expr="$rice_chalkiness > 30 AND $rice_head_rice_recovery >= 60",
        consequence="垩白区域结构疏松，碾磨时极易碎裂，整精米率无法保证。",
        confidence=0.85,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "稻米碾磨品质研究", "垩白与整精米率的负相关关系"),
            CorrelationEvidence(EvidenceLevel.STRONG, "中国优质稻谷标准 GB/T 17891", "垩白度和整精米率的品质要求"),
        ],
        tags=["品质", "碾磨"],
    ),
    BiologicalConstraint(
        id="rice_grain_length_head_rice",
        name="极端粒长与整精米率的约束",
        description="粒长超过 8.5mm 的品种，整精米率很难达到 55% 以上。",
        severity=ConstraintSeverity.WARNING,
        scope=ConstraintScope.SPECIES,
        species="水稻",
        condition_expr="$rice_grain_length > 8.5 AND $rice_head_rice_recovery >= 55",
        consequence="过长的籽粒在碾磨过程中容易断裂，整精米率下降。",
        confidence=0.75,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "稻米碾磨品质研究", "粒长与整精米率的负相关"),
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "部分长粒品种数据", "粒长超过 8mm 后整精米率显著下降"),
        ],
        tags=["粒型", "碾磨"],
    ),
    BiologicalConstraint(
        id="rice_drought_severe_yield_loss",
        name="严重干旱的产量损失下限",
        description="在严重干旱胁迫下（土壤水势 < -1.5 MPa），即使是最耐旱的品种，产量损失也不可能低于 30%。",
        severity=ConstraintSeverity.FATAL,
        scope=ConstraintScope.SPECIES,
        species="水稻",
        condition_expr="$rice_drought_tolerance >= 8 AND $drought_severity = 'severe'",
        consequence="严重干旱导致光合作用停止、叶片卷曲、籽粒灌浆终止，产量损失不可避免。",
        confidence=0.85,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "IRRI 耐旱研究", "严重干旱下的产量损失数据"),
            CorrelationEvidence(EvidenceLevel.STRONG, "作物抗旱生理学", "干旱胁迫对产量形成的影响机制"),
        ],
        tags=["耐旱", "产量损失"],
    ),
    BiologicalConstraint(
        id="rice_cold_tropical",
        name="热带品种的耐冷限制",
        description="纯热带血统的品种（无耐冷基因导入）在低于 15°C 的环境下几乎无法正常结实。",
        severity=ConstraintSeverity.FATAL,
        scope=ConstraintScope.SUBSPECIES,
        species="水稻",
        condition_expr="$rice_cold_tolerance <= 3 AND $temperature < 15",
        consequence="低温导致花粉活力下降、授粉受精失败、籽粒灌浆停止。",
        confidence=0.80,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "水稻耐冷性研究", "热带品种的低温敏感性"),
            CorrelationEvidence(EvidenceLevel.STRONG, "水稻生态适应性研究", "不同生态型品种的温度适应范围"),
        ],
        tags=["耐冷", "生态型"],
    ),
    BiologicalConstraint(
        id="rice_nitrogen_protein_quality",
        name="高氮与蛋白质含量的关联",
        description="施氮量超过 200 kg/ha 时，蛋白质含量通常超过 10%，可能影响食味品质。",
        severity=ConstraintSeverity.WARNING,
        scope=ConstraintScope.SPECIES,
        species="水稻",
        condition_expr="$nitrogen_rate > 200 AND $rice_protein_content > 10",
        consequence="蛋白质含量过高会掩盖直链淀粉对食味的影响，导致米饭口感变差。",
        confidence=0.70,
        evidence=[
            CorrelationEvidence(EvidenceLevel.STRONG, "氮肥与稻米品质研究", "施氮量与蛋白质含量的正相关"),
            CorrelationEvidence(EvidenceLevel.SUGGESTED, "食味品质研究", "蛋白质含量对食味的影响"),
        ],
        tags=["氮肥", "品质"],
    ),
]
