<#
.SYNOPSIS
    multi_factor_lab 阶段四一键复现脚本（M0–M5）

.DESCRIPTION
    按 M0 → M5 顺序执行全部核心脚本，失败即停，记录每步耗时。
    支持 -DryRun（只列清单）和 -SkipHeavy（跳过 v2 重训练）。

.PARAMETER DryRun
    只打印任务清单，不实际执行。

.PARAMETER SkipHeavy
    跳过 composite_factors_lasso_horizon_v2.py（重训练，约 10-20 分钟）。
    要求 composite_scores_lasso_horizon_all8_v2.parquet 已存在。

.PARAMETER Stages
    只跑指定阶段，如 -Stages M1,M2。默认全部。

.EXAMPLE
    .\run_all_stage4.ps1 -DryRun
    .\run_all_stage4.ps1 -SkipHeavy
    .\run_all_stage4.ps1 -Stages M1,M2
#>
param(
    [switch]$DryRun,
    [switch]$SkipHeavy,
    [string[]]$Stages = @("M0", "M1", "M2", "M3", "M4", "M5")
)

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$ROOT = "C:\Users\16075\code\multi_factor_lab"
Set-Location $ROOT

# ---------------- 任务定义 ----------------
# 每项: @{ Name; Cmd; Heavy; Requires }
# Requires: 运行前必须存在的文件（相对路径），不存在则报错跳过

$TASKS = [ordered]@{
    M0 = @(
        @{ Name = "check_data"; Cmd = "python scripts/stage4/check_data.py"; Heavy = $false; Requires = @() }
    )
    M1 = @(
        @{ Name = "m1_precheck";      Cmd = "python scripts/stage4/attribution/m1_precheck.py";      Heavy = $false; Requires = @() }
        @{ Name = "brinson";          Cmd = "python scripts/stage4/attribution/brinson.py";          Heavy = $false; Requires = @() }
        @{ Name = "brinson_detail";   Cmd = "python scripts/stage4/attribution/brinson_detail.py";   Heavy = $false; Requires = @() }
        @{ Name = "m1_reconcile";     Cmd = "python scripts/stage4/attribution/m1_reconcile.py";     Heavy = $false; Requires = @() }
        @{ Name = "make_brinson_fig"; Cmd = "python scripts/stage4/report/make_brinson_figures.py";  Heavy = $false; Requires = @() }
    )
    M2 = @(
        @{ Name = "m2_precheck";      Cmd = "python scripts/stage4/attribution/m2_precheck.py";      Heavy = $false; Requires = @() }
        @{ Name = "m2_attribution";   Cmd = "python scripts/stage4/attribution/m2_attribution.py --full"; Heavy = $false; Requires = @() }
        @{ Name = "m2_diagnose";      Cmd = "python scripts/stage4/attribution/m2_diagnose.py";      Heavy = $false; Requires = @() }
        @{ Name = "make_factor_fig";  Cmd = "python scripts/stage4/report/make_factor_figures.py";   Heavy = $false; Requires = @() }
    )
    M3 = @(
        @{ Name = "m3_rebuild_daily"; Cmd = "python scripts/stage4/attribution/m3_rebuild_daily_nav.py"; Heavy = $false; Requires = @() }
        @{ Name = "m3_risk";          Cmd = "python scripts/stage4/attribution/m3_risk.py";           Heavy = $false; Requires = @() }
        @{ Name = "m3_factor_risk";   Cmd = "python scripts/stage4/attribution/m3_factor_risk.py";    Heavy = $false; Requires = @() }
        @{ Name = "m3_tail";          Cmd = "python scripts/stage4/attribution/m3_tail.py";           Heavy = $false; Requires = @() }
        @{ Name = "m3_mdd";           Cmd = "python scripts/stage4/attribution/m3_mdd.py";            Heavy = $false; Requires = @() }
        @{ Name = "make_m3_fig";      Cmd = "python scripts/stage4/report/make_m3_figures.py";        Heavy = $false; Requires = @() }
    )
    M4 = @(
        @{ Name = "m4a_target_vol";   Cmd = "python scripts/stage4/position/m4a_target_vol.py";     Heavy = $false; Requires = @() }
        @{ Name = "m4a_backtest";     Cmd = "python scripts/stage4/position/m4a_backtest.py";       Heavy = $false; Requires = @("data/processed/m4a_position_series.parquet") }
        @{ Name = "m4b_stop_loss";    Cmd = "python scripts/stage4/position/m4b_stop_loss.py";      Heavy = $false; Requires = @() }
        @{ Name = "m4b_backtest";     Cmd = "python scripts/stage4/position/m4b_backtest.py";       Heavy = $false; Requires = @() }
        @{ Name = "m4b_final";        Cmd = "python scripts/stage4/position/m4b_final.py";          Heavy = $false; Requires = @("data/processed/m4a_position_series.parquet", "data/processed/bt_nav_lasso_horizon_all8_daily.parquet") }
        @{ Name = "m4_final_bt";      Cmd = "python scripts/stage4/position/m4_final_backtest.py";  Heavy = $false; Requires = @("data/processed/m4_position_series.parquet") }
        @{ Name = "v2_retrain";       Cmd = "python scripts/backtest/composite_factors_lasso_horizon_v2.py"; Heavy = $true; Requires = @() }
        @{ Name = "m4c_final";        Cmd = "python scripts/stage4/position/m4c_final.py";           Heavy = $false; Requires = @("data/processed/composite_scores_lasso_horizon_all8_v2.parquet", "data/processed/m4_position_series.parquet") }
        @{ Name = "m4c_backtest";     Cmd = "python scripts/stage4/position/m4c_backtest.py";        Heavy = $false; Requires = @("data/processed/composite_scores_lasso_horizon_all8_v2.parquet") }
        @{ Name = "m4_rebuild_daily"; Cmd = "python scripts/stage4/position/m4_rebuild_daily_nav.py"; Heavy = $false; Requires = @("data/processed/m4_final_holdings.csv", "data/processed/m4_final_periods.csv") }
        @{ Name = "make_m4_fig";      Cmd = "python scripts/stage4/position/make_m4_figures.py";     Heavy = $false; Requires = @() }
    )
    M5 = @(
        @{ Name = "m5_0_audit";       Cmd = "python scripts/stage4/validate/m5_0_audit.py";        Heavy = $false; Requires = @() }
        @{ Name = "m5_1c_reconcile";  Cmd = "python scripts/stage4/validate/m5_1c_reconcile.py";   Heavy = $false; Requires = @() }
        @{ Name = "m5_1c_fix";        Cmd = "python scripts/stage4/validate/m5_1c_fix.py";         Heavy = $false; Requires = @("data/processed/m4c_bt_periods.csv", "data/processed/m4_bt_periods.csv") }
        @{ Name = "m5_2_sens";        Cmd = "python scripts/stage4/validate/m5_2_sensitivity.py";  Heavy = $false; Requires = @() }
        @{ Name = "m5_2c_diag";       Cmd = "python scripts/stage4/validate/m5_2c_smooth_diag.py"; Heavy = $false; Requires = @() }
        @{ Name = "m5_2d_v1_ctrl";    Cmd = "python scripts/stage4/validate/m5_2d_v1_control.py";  Heavy = $false; Requires = @() }
    )
}

# ---------------- 工具函数 ----------------
function Test-Prereqs {
    param([string[]]$Files)
    $missing = @()
    foreach ($f in $Files) {
        if (-not (Test-Path (Join-Path $ROOT $f))) { $missing += $f }
    }
    return $missing
}

function Format-Elapsed {
    param([timespan]$ts)
    if ($ts.TotalMinutes -ge 1) { return ("{0:N1} min" -f $ts.TotalMinutes) }
    return ("{0:N1} s" -f $ts.TotalSeconds)
}

# ---------------- 预检 ----------------
Write-Host ""
Write-Host "==============================================================="
Write-Host " multi_factor_lab 阶段四一键复现 (M0-M5)"
Write-Host "==============================================================="
Write-Host (" ROOT      : {0}" -f $ROOT)
Write-Host (" Stages    : {0}" -f ($Stages -join ", "))
Write-Host (" DryRun    : {0}" -f $DryRun)
Write-Host (" SkipHeavy : {0}" -f $SkipHeavy)
Write-Host ""

if ($SkipHeavy -and -not (Test-Path (Join-Path $ROOT "data/processed/composite_scores_lasso_horizon_all8_v2.parquet"))) {
    Write-Host "[ERROR] -SkipHeavy 已开启，但 v2 scores 不存在，无法跳过 v2 重训练。" -ForegroundColor Red
    Write-Host "        请先不带 -SkipHeavy 跑一次，或手动执行："
    Write-Host "        python scripts/backtest/composite_factors_lasso_horizon_v2.py"
    exit 1
}

# ---------------- DryRun 清单 ----------------
if ($DryRun) {
    Write-Host "===== 任务清单（DryRun，不执行）====="
    foreach ($stage in $Stages) {
        if (-not $TASKS.Contains($stage)) {
            Write-Host ("  [{0}] 未知阶段，跳过" -f $stage) -ForegroundColor Yellow
            continue
        }
        Write-Host ""
        Write-Host ("--- {0} ---" -f $stage) -ForegroundColor Cyan
        foreach ($t in $TASKS[$stage]) {
            $flag = if ($t.Heavy) { " [HEAVY]" } else { "" }
            $skip = ""
            if ($t.Heavy -and $SkipHeavy) { $skip = " [SKIP by -SkipHeavy]" }
            Write-Host ("  {0,-20}{1}{2}" -f $t.Name, $flag, $skip)
            Write-Host ("    {0}" -f $t.Cmd) -ForegroundColor DarkGray
            if ($t.Requires.Count -gt 0) {
                Write-Host ("    requires: {0}" -f ($t.Requires -join ", ")) -ForegroundColor DarkGray
            }
        }
    }
    Write-Host ""
    Write-Host "[DryRun 结束] 去掉 -DryRun 即可实际执行。" -ForegroundColor Green
    exit 0
}

# ---------------- 执行 ----------------
$TotalSw = [System.Diagnostics.Stopwatch]::StartNew()
$Done = @()
$Failed = @()
$Skipped = @()
$NotRun = @()

$currentStage = $null
foreach ($stage in $Stages) {
    if (-not $TASKS.Contains($stage)) {
        Write-Host ("[WARN] 未知阶段 {0}，跳过" -f $stage) -ForegroundColor Yellow
        continue
    }
    $currentStage = $stage
    Write-Host ""
    Write-Host ("========== {0} ==========" -f $stage) -ForegroundColor Cyan

    foreach ($t in $TASKS[$stage]) {
        if ($t.Heavy -and $SkipHeavy) {
            Write-Host ("  [SKIP] {0} (Heavy, -SkipHeavy)" -f $t.Name) -ForegroundColor Yellow
            $Skipped += ("{0}/{1}" -f $stage, $t.Name)
            continue
        }

        $missing = Test-Prereqs -Files $t.Requires
        if ($missing.Count -gt 0) {
            Write-Host ("  [SKIP] {0} 缺少前置产物:" -f $t.Name) -ForegroundColor Yellow
            foreach ($m in $missing) { Write-Host ("         - {0}" -f $m) -ForegroundColor Yellow }
            $Skipped += ("{0}/{1}" -f $stage, $t.Name)
            continue
        }

        Write-Host ("  [RUN ] {0}" -f $t.Name) -ForegroundColor Green
        Write-Host ("         {0}" -f $t.Cmd) -ForegroundColor DarkGray
        $sw = [System.Diagnostics.Stopwatch]::StartNew()

        $cmd = $t.Cmd
        Invoke-Expression $cmd
        $code = $LASTEXITCODE

        $sw.Stop()
        if ($code -ne 0) {
            Write-Host ("  [FAIL] {0}  exit={1}  耗时={2}" -f $t.Name, $code, (Format-Elapsed $sw.Elapsed)) -ForegroundColor Red
            $Failed += ("{0}/{1}" -f $stage, $t.Name)
            # 标记剩余任务为未执行
            $foundFail = $false
            foreach ($stage2 in $Stages) {
                if (-not $TASKS.Contains($stage2)) { continue }
                foreach ($t2 in $TASKS[$stage2]) {
                    if ($foundFail) {
                        $NotRun += ("{0}/{1}" -f $stage2, $t2.Name)
                    }
                    if ($stage2 -eq $stage -and $t2.Name -eq $t.Name) { $foundFail = $true }
                }
            }
            break
        }
        Write-Host ("  [ OK ] {0}  耗时={1}" -f $t.Name, (Format-Elapsed $sw.Elapsed)) -ForegroundColor Green
        $Done += ("{0}/{1}" -f $stage, $t.Name)
    }

    if ($Failed.Count -gt 0) { break }
}

$TotalSw.Stop()

# ---------------- 汇总 ----------------
Write-Host ""
Write-Host "==============================================================="
Write-Host " 汇总"
Write-Host "==============================================================="
Write-Host (" 总耗时    : {0}" -f (Format-Elapsed $TotalSw.Elapsed))
Write-Host (" 成功      : {0}" -f $Done.Count)
Write-Host (" 跳过      : {0}" -f $Skipped.Count)
Write-Host (" 失败      : {0}" -f $Failed.Count)
Write-Host (" 未执行    : {0}" -f $NotRun.Count)

if ($Skipped.Count -gt 0) {
    Write-Host ""
    Write-Host " 跳过任务:" -ForegroundColor Yellow
    $Skipped | ForEach-Object { Write-Host ("   - {0}" -f $_) -ForegroundColor Yellow }
}
if ($Failed.Count -gt 0) {
    Write-Host ""
    Write-Host " 失败任务:" -ForegroundColor Red
    $Failed | ForEach-Object { Write-Host ("   - {0}" -f $_) -ForegroundColor Red }
    Write-Host ""
    Write-Host "[退出码 1] 有任务失败，请检查上方红色日志。" -ForegroundColor Red
    exit 1
}
if ($NotRun.Count -gt 0) {
    Write-Host ""
    Write-Host " 未执行任务:" -ForegroundColor DarkYellow
    $NotRun | ForEach-Object { Write-Host ("   - {0}" -f $_) -ForegroundColor DarkYellow }
}

Write-Host ""
Write-Host "[全部完成]" -ForegroundColor Green
exit 0