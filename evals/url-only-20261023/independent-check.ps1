param([string]$InputCsv = (Join-Path $PSScriptRoot 'input.csv'))
$ErrorActionPreference = 'Stop'
$rows = @(Import-Csv -LiteralPath $InputCsv)
if ($rows.Count -ne 24) { throw 'Expected 24 supplied synthetic rows' }
$daily = foreach ($group in ($rows | Group-Object day)) {
    $truth = 0.0; $time = 0.0; $neighbor = 0.0; $selected = 0.0
    $complete = $true
    foreach ($row in $group.Group) {
        $truth += [double]$row.true_count
        if ($row.observed_count -ne '') {
            $time += [double]$row.observed_count
            $neighbor += [double]$row.observed_count
            $selected += [double]$row.observed_count
        } else {
            $time += [double]$row.time_estimate
            if ($row.neighbor_estimate -eq '') { $complete = $false }
            else { $neighbor += [double]$row.neighbor_estimate }
            if ($row.choice -eq 'time') { $selected += [double]$row.time_estimate }
            elseif ($row.choice -eq 'neighbor' -and $row.neighbor_estimate -ne '') { $selected += [double]$row.neighbor_estimate }
            else { throw 'Invalid or unavailable selected candidate' }
        }
    }
    [pscustomobject]@{day=$group.Name; truth=$truth; time=$time; neighbor=$(if($complete){$neighbor}else{$null}); selected=$selected; complete=$complete}
}
function Get-Rmse($items, [string]$method) {
    $sum = 0.0
    foreach ($item in $items) { $sum += [math]::Pow(($item.$method - $item.truth), 2) }
    [math]::Sqrt($sum / $items.Count)
}
$common = @($daily | Where-Object complete)
$result = [ordered]@{
    rows=$rows.Count; days=$daily.Count; common_days=$common.Count
    daily=@($daily)
    all_time_rmse=(Get-Rmse $daily 'time')
    all_selected_rmse=(Get-Rmse $daily 'selected')
    common_time_rmse=(Get-Rmse $common 'time')
    common_neighbor_rmse=(Get-Rmse $common 'neighbor')
    common_selected_rmse=(Get-Rmse $common 'selected')
    harmful_days=@($common | Where-Object { [math]::Abs($_.neighbor-$_.truth) -gt [math]::Abs($_.time-$_.truth) } | ForEach-Object day)
    helpful_days=@($common | Where-Object { [math]::Abs($_.neighbor-$_.truth) -lt [math]::Abs($_.time-$_.truth) } | ForEach-Object day)
}
$result | ConvertTo-Json -Depth 8
