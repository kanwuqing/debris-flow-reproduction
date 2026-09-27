## 规模
events=186 dfid=186 with_CID=167 time_missing=95
rain_files=465 folders=147 named=465 gauges=39
catchments=79 with_dam=23 dams=55 no_dam=56 zero_event=12
area_sum=851.0 med=5.59 max=54.73
area_err_max=2.52e-06 over1pct=0
corr_area_events=-0.0175 corr_area_dam=0.5133
events_by_year=2008:29, 2009:6, 2010:98, 2011:22, 2012:1, 2013:16, 2016:1, 2019:12, 2020:1
rain_folders_missing_in_events=0

## Task A 样本
rows=1597 pos=444 neg=1153 rate=0.2780 events=146 gauges=39
csv rows=1597 pos=444 events_with_label=144 years=2008-2020
id_pairs={'n_rows': 11179, 'windows': [1, 3, 6, 12, 24, 48, 72]}
temporal={'train_years': [2008.0, 2009.0, 2010.0, 2011.0, 2012.0, 2013.0], 'test_years': [2016.0, 2019.0, 2020.0], 'n_train': 1540, 'n_test': 57}

## Task A 分布（触发 vs 非触发，中位数 / 均值）
total_mm: trig_med=49.10 trig_mean=111.48 nont_med=9.00 nont_mean=26.99
duration_h: trig_med=20.00 trig_mean=27.95 nont_med=8.00 nont_mean=8.80
n_wet_hours: trig_med=19.00 trig_mean=24.37 nont_med=5.00 nont_mean=6.53
max_1h: trig_med=15.90 trig_mean=17.90 nont_med=4.90 nont_mean=12.09
max_24h: trig_med=44.80 trig_mean=84.84 nont_med=9.00 nont_mean=26.72
max_72h: trig_med=49.10 trig_mean=111.27 nont_med=9.00 nont_mean=26.99
mean_intensity: trig_med=2.62 trig_mean=4.18 nont_med=2.15 nont_mean=2.87
antecedent_24h: trig_med=29.40 trig_mean=34.73 nont_med=0.00 nont_mean=6.35
antecedent_72h: trig_med=34.40 trig_mean=41.89 nont_med=1.20 nont_mean=16.86
api: trig_med=5.06 trig_mean=8.19 nont_med=0.07 nont_mean=1.46
trigger_overlap_zero=7/444

## Task A 三协议（metrics_summary.csv）
random       logistic_regression  acc=0.9125 prec=0.8182 rec=0.8797 f1=0.8478 auc=0.9214 cm=[[321, 26], [16, 117]]
random       random_forest        acc=0.9625 prec=0.9389 rec=0.9248 f1=0.9318 auc=0.9876 cm=[[339, 8], [10, 123]]
random       svm_rbf              acc=0.9250 prec=0.8593 rec=0.8722 f1=0.8657 auc=0.9224 cm=[[328, 19], [17, 116]]
random       gradient_boosting    acc=0.9583 prec=0.9313 rec=0.9173 f1=0.9242 auc=0.9785 cm=[[338, 9], [11, 122]]
random       xgboost              acc=0.9646 prec=0.9462 rec=0.9248 f1=0.9354 auc=0.9890 cm=[[340, 7], [10, 123]]
group_event  logistic_regression  acc=0.9036 prec=0.8059 rec=0.8604 f1=0.8322 auc=0.9225 cm=[[1061, 92], [62, 382]]
group_event  random_forest        acc=0.9562 prec=0.9329 rec=0.9077 f1=0.9201 auc=0.9832 cm=[[1124, 29], [41, 403]]
group_event  svm_rbf              acc=0.9180 prec=0.8323 rec=0.8829 f1=0.8568 auc=0.9340 cm=[[1074, 79], [52, 392]]
group_event  gradient_boosting    acc=0.9555 prec=0.9388 rec=0.8986 f1=0.9183 auc=0.9735 cm=[[1127, 26], [45, 399]]
group_event  xgboost              acc=0.9580 prec=0.9415 rec=0.9054 f1=0.9231 auc=0.9802 cm=[[1128, 25], [42, 402]]
temporal     logistic_regression  acc=0.9825 prec=0.9583 rec=1.0000 f1=0.9787 auc=0.9949 cm=[[33, 1], [0, 23]]
temporal     random_forest        acc=0.8947 prec=1.0000 rec=0.7391 f1=0.8500 auc=0.9987 cm=[[34, 0], [6, 17]]
temporal     svm_rbf              acc=0.9825 prec=0.9583 rec=1.0000 f1=0.9787 auc=0.9987 cm=[[33, 1], [0, 23]]
temporal     gradient_boosting    acc=0.8772 prec=1.0000 rec=0.6957 f1=0.8205 auc=0.9859 cm=[[34, 0], [7, 16]]
temporal     xgboost              acc=0.8772 prec=1.0000 rec=0.6957 f1=0.8205 auc=0.9923 cm=[[34, 0], [7, 16]]

## I-D 阈值
ols_all_points           I = 8.416 * D^(-0.8011)    r2=0.3503 acc=0.6456 prec=0.4361 rec=0.9369 f1=0.5951 tp=416 fp=538 fn=28 tn=615
ols_trigger_only         I = 17.72 * D^(-0.6521)    r2=0.4855 acc=0.6807 prec=0.4446 rec=0.5968 f1=0.5096 tp=265 fp=331 fn=179 tn=822
ols_trigger_minus_1sd    I = 6.829 * D^(-0.6521)    r2=0.4855 acc=0.6606 prec=0.4473 rec=0.9369 f1=0.6055 tp=416 fp=514 fn=28 tn=639
quantile_p50_trigger     I = 18.47 * D^(-0.7397)    r2=0.9909 acc=0.7120 prec=0.4881 rec=0.7365 f1=0.5871 tp=327 fp=343 fn=117 tn=810
quantile_p90_trigger     I = 47.35 * D^(-0.5535)    r2=0.9649 acc=0.7733 prec=0.9271 rec=0.2005 f1=0.3296 tp=89 fp=7 fn=355 tn=1146
quantile_p90_all         I = 43.81 * D^(-0.742)     r2=0.9911 acc=0.7558 prec=0.6154 rec=0.3243 f1=0.4248 tp=144 fp=90 fn=300 tn=1063
ml_equivalent={}

## Task A 特征重要性
RF n_wet_hours        0.1739
RF duration_h         0.1715
RF max_24h            0.0899
RF max_72h            0.0723
RF total_mm           0.0681
RF api                0.0643
RF antecedent_168h    0.0621
RF max_48h            0.0611
RF antecedent_72h     0.0522
RF antecedent_24h     0.0406
RF max_12h            0.0336
RF max_3h             0.0258
RF peak_intensity     0.0226
RF max_1h             0.0217
RF mean_intensity     0.0217
RF max_6h             0.0184
LR n_wet_hours        +4.1843
LR max_6h             +2.8813
LR max_3h             -2.1721
LR duration_h         -1.7689
LR max_12h            -1.7041
LR max_24h            +1.4236
LR api                +0.9429
LR antecedent_72h     -0.5546
LR antecedent_168h    +0.5042
LR antecedent_24h     -0.4894
LR mean_intensity     +0.4185
LR max_48h            -0.1104
LR peak_intensity     -0.0999
LR max_1h             -0.0999
LR max_72h            -0.0954
LR total_mm           -0.0934

## Task A 逐年触发
2008 rows=10 events=10 dur=13.4 tot=18.7 max1h=4.2 int=1.11
2009 rows=4 events=4 dur=23.5 tot=26.9 max1h=9.5 int=1.24
2010 rows=230 events=79 dur=15.9 tot=63.3 max1h=18.8 int=4.52
2011 rows=45 events=21 dur=18.0 tot=47.3 max1h=13.0 int=2.84
2012 rows=2 events=1 dur=12.5 tot=79.7 max1h=37.9 int=8.17
2013 rows=130 events=15 dur=52.6 tot=221.1 max1h=18.4 int=4.31
2016 rows=8 events=1 dur=35.0 tot=91.5 max1h=14.3 int=2.56
2019 rows=14 events=12 dur=36.7 tot=181.3 max1h=24.6 int=4.82
2020 rows=1 events=1 dur=59.0 tot=344.7 max1h=32.6 int=5.84

## Task B
rows=79 pos=35 neg=44 median=1.0 rule=susceptible = (n_events > median(n_events))
excluded=['n_events', 'first_event', 'last_event', 'total_volume_m3', 'event_span_years']
logistic_regression  acc=0.7598+-0.0970 prec=0.7543 rec=0.7429 f1=0.7307+-0.1079 auc=0.8082
random_forest        acc=0.7277+-0.0847 prec=0.6920 rec=0.7457 f1=0.7001+-0.1125 auc=0.7951
svm_rbf              acc=0.7115+-0.1129 prec=0.6833 rec=0.7057 f1=0.6738+-0.1504 auc=0.7822
gradient_boosting    acc=0.7140+-0.1091 prec=0.7043 rec=0.6800 f1=0.6737+-0.1262 auc=0.7992
xgboost              acc=0.7326+-0.0803 prec=0.7101 rec=0.7029 f1=0.6927+-0.1070 auc=0.8186
OOF random_forest: acc=0.7468 prec=0.7027 rec=0.7429 f1=0.7222 cm=[[33, 11], [9, 26]]
OOF logistic_regression: acc=0.7342 prec=0.7059 rec=0.6857 f1=0.6957 cm=[[34, 10], [11, 24]]
B-RF centroid_lat       0.1543
B-RF n_gullies          0.1272
B-RF poly_perimeter_km  0.1127
B-RF bbox_height_km     0.1109
B-RF area_km2           0.0955
B-RF compactness        0.0885
B-RF centroid_lon       0.0860
B-RF bbox_aspect        0.0787
B-RF bbox_width_km      0.0740
B-RF dam_number         0.0366
B-RF has_dam            0.0155
B-RF has_built_year     0.0144
B-RF built_year         0.0058
B-LR n_gullies          +1.9491
B-LR compactness        +0.6170
B-LR centroid_lat       -0.5265
B-LR poly_perimeter_km  +0.4610
B-LR dam_number         +0.4310
B-LR centroid_lon       -0.3197
B-LR bbox_width_km      +0.2866
B-LR area_km2           +0.2082
B-LR bbox_height_km     -0.1581
B-LR built_year         +0.1418
B-LR has_built_year     +0.1331
B-LR has_dam            +0.1326
B-LR bbox_aspect        -0.1313

## Task B 交叉表
dams=0: catch=56 events=105 mean=1.88 high=20/56
dams=1: catch=9 events=25 mean=2.78 high=4/9
dams=2: catch=3 events=9 mean=3.00 high=3/3
dams=>=3: catch=11 events=28 mean=2.55 high=8/11
built=0: catch=57 events=122 mean=2.14
built=2011: catch=6 events=9 mean=1.50
built=2012: catch=1 events=3 mean=3.00
built=2013: catch=12 events=19 mean=1.58
built=2014: catch=2 events=10 mean=5.00
built=2018: catch=1 events=4 mean=4.00
prevented=False: catch=62 events=134 mean=2.16
prevented=True: catch=17 events=33 mean=1.94
