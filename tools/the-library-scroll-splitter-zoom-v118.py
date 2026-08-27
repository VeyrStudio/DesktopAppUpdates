from pathlib import Path
import base64, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
TF=ROOT/"the-library"
VERSION="1.0.18"

manifest=json.loads((TF/"manifest.json").read_text(encoding="utf-8"))
if manifest.get("version")!="1.0.17":
    raise SystemExit(f"Expected live base 1.0.17, got {manifest.get('version')}")

dropin=r"""# THE LIBRARY SCROLL SPLITTER + ZOOM v1.0.18
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$script:LibraryMultiScrollHost=$null
$script:LibraryMultiScrollStates=@()
$script:LibraryRegularVisibility=@()
$script:RegularWrapViewport=$null
$script:RegularWrapZoomPercent=100
$script:RegularSplitMode='Buttons'
$script:RegularSplitDragWhich=''

function Get-LibraryAllChildControls($Root){
    $list=@()
    if($null -eq $Root){return $list}
    foreach($control in @($Root.Controls)){
        $list += $control
        if($null -ne $control.Controls -and $control.Controls.Count -gt 0){
            $list += @(Get-LibraryAllChildControls $control)
        }
    }
    return $list
}

function Open-LibraryScrollBitmap([string]$Path){
    if([string]::IsNullOrWhiteSpace($Path)){throw 'Image path is empty.'}
    if(-not(Test-Path -LiteralPath $Path -PathType Leaf)){throw ('Image file was not found: '+$Path)}

    $bytes=$null
    $stream=$null
    $source=$null
    $copy=$null
    try{
        $bytes=[IO.File]::ReadAllBytes($Path)
        if($null -eq $bytes -or $bytes.Length -eq 0){throw 'Image file is empty.'}
        $stream=New-Object IO.MemoryStream(,$bytes)
        $source=[Drawing.Image]::FromStream($stream,$true,$true)
        if($null -eq $source){throw 'Windows could not decode the image.'}
        $copy=New-Object Drawing.Bitmap($source)
        if($null -eq $copy -or $copy.Width -le 0 -or $copy.Height -le 0){throw 'Windows could not create the cover bitmap.'}
        return $copy
    }
    catch{
        if($null -ne $copy){try{$copy.Dispose()}catch{}}
        throw
    }
    finally{
        if($null -ne $source){try{$source.Dispose()}catch{}}
        if($null -ne $stream){try{$stream.Dispose()}catch{}}
    }
}

function New-LibraryScrollLabel([string]$Text,[int]$X,[int]$Y,[int]$W=150,[int]$H=22){
    $label=New-Object Windows.Forms.Label
    $label.Text=$Text
    $label.Location=New-Object Drawing.Point($X,$Y)
    $label.Size=New-Object Drawing.Size($W,$H)
    $label.ForeColor=[Drawing.Color]::Gainsboro
    return $label
}

function New-LibraryScrollTextBox([int]$X,[int]$Y,[int]$W){
    $box=New-Object Windows.Forms.TextBox
    $box.Location=New-Object Drawing.Point($X,$Y)
    $box.Size=New-Object Drawing.Size($W,25)
    return $box
}

function New-LibraryScrollCoverType([int]$X,[int]$Y,[int]$W){
    $combo=New-Object Windows.Forms.ComboBox
    $combo.Location=New-Object Drawing.Point($X,$Y)
    $combo.Size=New-Object Drawing.Size($W,27)
    $combo.DropDownStyle='DropDownList'
    if($null -ne $cmbWrapCoverType){
        foreach($item in @($cmbWrapCoverType.Items)){[void]$combo.Items.Add([string]$item)}
        if(-not [string]::IsNullOrWhiteSpace([string]$cmbWrapCoverType.Text)){
            $combo.Text=[string]$cmbWrapCoverType.Text
        }
    }
    if($combo.Items.Count -eq 0){
        foreach($item in @('Unsorted','Paperback','Hardcover','Ebook','Dust Jacket')){[void]$combo.Items.Add($item)}
    }
    if($combo.SelectedIndex -lt 0 -and $combo.Items.Count -gt 0){$combo.SelectedIndex=0}
    return $combo
}

function Update-LibraryScrollZoom($State){
    if($null -eq $State -or $null -eq $State.Bitmap -or $null -eq $State.Viewport -or $null -eq $State.Picture){return}
    $vw=[math]::Max(40,$State.Viewport.ClientSize.Width-4)
    $vh=[math]::Max(40,$State.Viewport.ClientSize.Height-4)
    $fit=[math]::Min($vw/[double]$State.Bitmap.Width,$vh/[double]$State.Bitmap.Height)
    if($fit -le 0){$fit=1.0}
    $zoom=[math]::Max(50,[math]::Min(400,[int]$State.ZoomPercent))
    $State.ZoomPercent=$zoom
    $scale=$fit*($zoom/100.0)
    $w=[math]::Max(1,[int][math]::Round($State.Bitmap.Width*$scale))
    $h=[math]::Max(1,[int][math]::Round($State.Bitmap.Height*$scale))
    $State.Picture.Size=New-Object Drawing.Size($w,$h)

    $x=if($w -lt $vw){[int](($vw-$w)/2)}else{0}
    $y=if($h -lt $vh){[int](($vh-$h)/2)}else{0}
    if($State.Viewport.AutoScrollPosition.X -eq 0 -and $State.Viewport.AutoScrollPosition.Y -eq 0){
        $State.Picture.Location=New-Object Drawing.Point($x,$y)
    }else{
        $State.Picture.Location=New-Object Drawing.Point(0,0)
    }

    if($null -ne $State.ZoomLabel){$State.ZoomLabel.Text=([string]$zoom+'%')}
    $State.Picture.Invalidate()
}

function Set-LibraryScrollZoom($State,[int]$Percent){
    if($null -eq $State){return}
    $State.ZoomPercent=[math]::Max(50,[math]::Min(400,$Percent))
    Update-LibraryScrollZoom $State
}

function Set-LibraryScrollMode($State,[string]$Mode){
    if($null -eq $State){return}
    if($Mode -eq 'Drag'){
        $State.Mode='Drag'
        $State.LeftNum.Enabled=$false
        $State.RightNum.Enabled=$false
        $State.ModeButton.Text='MODE: DRAG LINES'
        $State.Picture.Cursor=[Windows.Forms.Cursors]::VSplit
    }else{
        $State.Mode='Buttons'
        $State.DragWhich=''
        $State.LeftNum.Enabled=$true
        $State.RightNum.Enabled=$true
        $State.ModeButton.Text='MODE: BUTTONS'
        $State.Picture.Cursor=[Windows.Forms.Cursors]::Default
    }
    $State.Picture.Invalidate()
}

function Update-LibraryScrollState($State){
    if($null -eq $State -or $null -eq $State.Bitmap){return}
    $left=[int]$State.LeftNum.Value
    $right=[int]$State.RightNum.Value
    if($left -ge $right){
        if($State.LeftNum.Focused){
            $right=[math]::Min([int]$State.RightNum.Maximum,$left+1)
            $State.RightNum.Value=[decimal]$right
        }else{
            $left=[math]::Max([int]$State.LeftNum.Minimum,$right-1)
            $State.LeftNum.Value=[decimal]$left
        }
    }
    $State.Left=$left
    $State.Right=$right
    $State.BackDims.Text=("Back: {0} px" -f $left)
    $State.SpineDims.Text=("Spine: {0} px" -f ($right-$left))
    $State.FrontDims.Text=("Front: {0} px" -f ($State.Bitmap.Width-$right))
    $State.Picture.Invalidate()
}

function Set-LibraryScrollGuideAt($State,[string]$Which,[int]$MouseX){
    if($null -eq $State -or $null -eq $State.Bitmap -or $null -eq $State.Picture){return}
    $pw=[math]::Max(1,$State.Picture.ClientSize.Width)
    $px=[int][math]::Round(($MouseX/[double]$pw)*$State.Bitmap.Width)
    $px=[math]::Max(1,[math]::Min($State.Bitmap.Width-1,$px))

    if($Which -eq 'Left'){
        $px=[math]::Min($px,[int]$State.RightNum.Value-1)
        $px=[math]::Max([int]$State.LeftNum.Minimum,[math]::Min([int]$State.LeftNum.Maximum,$px))
        $State.LeftNum.Value=[decimal]$px
    }elseif($Which -eq 'Right'){
        $px=[math]::Max($px,[int]$State.LeftNum.Value+1)
        $px=[math]::Max([int]$State.RightNum.Minimum,[math]::Min([int]$State.RightNum.Maximum,$px))
        $State.RightNum.Value=[decimal]$px
    }
}

function Draw-LibraryScrollGuides($Sender,$EventArgs){
    $State=$Sender.Tag
    if($null -eq $State -or $null -eq $State.Bitmap -or $null -eq $EventArgs -or $null -eq $EventArgs.Graphics){return}
    $w=[math]::Max(1,$Sender.ClientSize.Width)
    $h=[math]::Max(1,$Sender.ClientSize.Height)
    $lx=([int]$State.LeftNum.Value/[double]$State.Bitmap.Width)*$w
    $rx=([int]$State.RightNum.Value/[double]$State.Bitmap.Width)*$w
    $color=if($State.Mode -eq 'Drag'){[Drawing.Color]::FromArgb(255,220,90)}else{[Drawing.Color]::White}
    $pen=New-Object Drawing.Pen($color,3)
    try{
        $pen.DashStyle=[Drawing.Drawing2D.DashStyle]::Dash
        $EventArgs.Graphics.DrawLine($pen,[float]$lx,0,[float]$lx,[float]$h)
        $EventArgs.Graphics.DrawLine($pen,[float]$rx,0,[float]$rx,[float]$h)
    }finally{
        $pen.Dispose()
    }
}

function Save-LibraryScrollCard($State){
    if($null -eq $State -or $null -eq $State.Bitmap){throw 'This cover editor no longer has an image.'}
    $left=[int]$State.LeftNum.Value
    $right=[int]$State.RightNum.Value
    if($left -le 0 -or $right -le $left -or $right -ge $State.Bitmap.Width){throw 'The split guide positions are invalid.'}

    $base=[IO.Path]::GetFileNameWithoutExtension([string]$State.Path)
    $pieces=@(
        @{Position='Back Cover';X=0;Width=$left;Label='Back Cover'},
        @{Position='Spine';X=$left;Width=($right-$left);Label='Spine'},
        @{Position='Front Cover';X=$right;Width=($State.Bitmap.Width-$right);Label='Front Cover'}
    )

    $created=@()
    try{
        foreach($piece in $pieces){
            $stored=Make-UniqueStoredName '.png'
            $dest=Join-Path $script:FilesRoot $stored
            Save-CropPng $State.Bitmap ([int]$piece.X) ([int]$piece.Width) $dest
            $created += $dest
            $script:PendingCoverType=[string]$State.CoverType.Text
            $recordArgs=@{
                OriginalName=(Make-SplitName $base $piece.Label)
                StoredName=$stored
                Position=$piece.Position
                Project=$State.Project.Text
                Ship=$State.Ship.Text
                Fandom=$State.Fandom.Text
                Tags=$State.Tags.Text
            }
            Add-LibraryRecord @recordArgs | Out-Null
        }

        Refresh-HierarchyTree
        Refresh-LibraryGrid
        $State.Status.Text='SAVED: BACK + SPINE + FRONT'
        $State.Status.ForeColor=[Drawing.Color]::LightGreen
        $State.SaveButton.Enabled=$false
        $State.Saved=$true
    }
    catch{
        foreach($file in @($created)){try{Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue}catch{}}
        throw
    }
}

function New-LibraryScrollCard([string]$Path,[int]$Ordinal,[int]$Total){
    $bitmap=Open-LibraryScrollBitmap $Path

    $card=New-Object Windows.Forms.Panel
    $card.Size=New-Object Drawing.Size(1135,835)
    $card.BorderStyle='FixedSingle'
    $card.BackColor=[Drawing.Color]::FromArgb(46,13,70)

    $header=New-LibraryScrollLabel ("COVER {0} OF {1}  -  {2}" -f $Ordinal,$Total,[IO.Path]::GetFileName($Path)) 14 10 1080 28
    $header.Font=New-Object Drawing.Font('Segoe UI Semibold',11)
    $card.Controls.Add($header)

    $viewport=New-Object Windows.Forms.Panel
    $viewport.Location=New-Object Drawing.Point(14,42)
    $viewport.Size=New-Object Drawing.Size(1105,430)
    $viewport.AutoScroll=$true
    $viewport.BackColor=[Drawing.Color]::FromArgb(25,8,38)
    $viewport.BorderStyle='FixedSingle'
    $card.Controls.Add($viewport)

    $picture=New-Object Windows.Forms.PictureBox
    $picture.SizeMode='StretchImage'
    $picture.Image=$bitmap
    $picture.TabStop=$true
    $picture.BackColor=[Drawing.Color]::Black
    $viewport.Controls.Add($picture)

    $zoomOut=New-Object Windows.Forms.Button
    $zoomOut.Text='−'
    $zoomOut.Location=New-Object Drawing.Point(14,485)
    $zoomOut.Size=New-Object Drawing.Size(42,30)
    $card.Controls.Add($zoomOut)

    $zoomLabel=New-LibraryScrollLabel '100%' 62 490 55 22
    $zoomLabel.TextAlign='MiddleCenter'
    $card.Controls.Add($zoomLabel)

    $zoomIn=New-Object Windows.Forms.Button
    $zoomIn.Text='+'
    $zoomIn.Location=New-Object Drawing.Point(123,485)
    $zoomIn.Size=New-Object Drawing.Size(42,30)
    $card.Controls.Add($zoomIn)

    $fit=New-Object Windows.Forms.Button
    $fit.Text='FIT'
    $fit.Location=New-Object Drawing.Point(175,485)
    $fit.Size=New-Object Drawing.Size(65,30)
    $card.Controls.Add($fit)

    $mode=New-Object Windows.Forms.Button
    $mode.Text='MODE: BUTTONS'
    $mode.Location=New-Object Drawing.Point(255,485)
    $mode.Size=New-Object Drawing.Size(170,30)
    $card.Controls.Add($mode)

    $hint=New-LibraryScrollLabel 'Ctrl + mouse wheel also zooms. Scrollbars pan while zoomed.' 445 490 480 22
    $hint.ForeColor=[Drawing.Color]::Silver
    $card.Controls.Add($hint)

    $card.Controls.Add((New-LibraryScrollLabel 'Back / Spine edge (px)' 14 530 165 22))
    $leftNum=New-Object Windows.Forms.NumericUpDown
    $leftNum.Location=New-Object Drawing.Point(182,526)
    $leftNum.Size=New-Object Drawing.Size(125,27)
    $leftNum.Minimum=1
    $leftNum.Maximum=[math]::Max(2,$bitmap.Width-2)
    $card.Controls.Add($leftNum)

    $card.Controls.Add((New-LibraryScrollLabel 'Spine / Front edge (px)' 335 530 175 22))
    $rightNum=New-Object Windows.Forms.NumericUpDown
    $rightNum.Location=New-Object Drawing.Point(514,526)
    $rightNum.Size=New-Object Drawing.Size(125,27)
    $rightNum.Minimum=2
    $rightNum.Maximum=[math]::Max(3,$bitmap.Width-1)
    $card.Controls.Add($rightNum)

    $auto=New-Object Windows.Forms.Button
    $auto.Text='AUTO DETECT SPINE'
    $auto.Location=New-Object Drawing.Point(665,522)
    $auto.Size=New-Object Drawing.Size(165,34)
    $card.Controls.Add($auto)

    $center=New-Object Windows.Forms.Button
    $center.Text='CENTERED GUESS'
    $center.Location=New-Object Drawing.Point(842,522)
    $center.Size=New-Object Drawing.Size(165,34)
    $card.Controls.Add($center)

    $backDims=New-LibraryScrollLabel 'Back: —' 14 562 230 22
    $spineDims=New-LibraryScrollLabel 'Spine: —' 255 562 230 22
    $frontDims=New-LibraryScrollLabel 'Front: —' 495 562 230 22
    $card.Controls.Add($backDims)
    $card.Controls.Add($spineDims)
    $card.Controls.Add($frontDims)

    $card.Controls.Add((New-LibraryScrollLabel 'Cover Type' 14 604 95 22))
    $coverType=New-LibraryScrollCoverType 112 600 200
    $card.Controls.Add($coverType)

    $card.Controls.Add((New-LibraryScrollLabel 'Project / Book' 335 604 105 22))
    $project=New-LibraryScrollTextBox 442 600 250
    $card.Controls.Add($project)

    $card.Controls.Add((New-LibraryScrollLabel 'Ship' 714 604 50 22))
    $ship=New-LibraryScrollTextBox 765 600 340
    $card.Controls.Add($ship)

    $card.Controls.Add((New-LibraryScrollLabel 'Fandom' 14 646 95 22))
    $fandom=New-LibraryScrollTextBox 112 642 300
    $card.Controls.Add($fandom)

    $card.Controls.Add((New-LibraryScrollLabel 'Extra Tags' 435 646 75 22))
    $tags=New-LibraryScrollTextBox 515 642 590
    $card.Controls.Add($tags)

    $save=New-Object Windows.Forms.Button
    $save.Text='SAVE BACK + SPINE + FRONT'
    $save.Location=New-Object Drawing.Point(14,698)
    $save.Size=New-Object Drawing.Size(250,42)
    $card.Controls.Add($save)

    $remove=New-Object Windows.Forms.Button
    $remove.Text='REMOVE THIS COVER'
    $remove.Location=New-Object Drawing.Point(278,698)
    $remove.Size=New-Object Drawing.Size(185,42)
    $card.Controls.Add($remove)

    $status=New-LibraryScrollLabel 'NOT SAVED' 485 707 360 24
    $status.Font=New-Object Drawing.Font('Segoe UI Semibold',10)
    $card.Controls.Add($status)

    $sourceNote=New-LibraryScrollLabel 'The full wrap is only the source image. The Library saves Back Cover, Spine, and Front Cover.' 14 758 900 28
    $sourceNote.ForeColor=[Drawing.Color]::Silver
    $card.Controls.Add($sourceNote)

    $state=[pscustomobject]@{
        Path=$Path
        Bitmap=$bitmap
        Card=$card
        Viewport=$viewport
        Picture=$picture
        LeftNum=$leftNum
        RightNum=$rightNum
        BackDims=$backDims
        SpineDims=$spineDims
        FrontDims=$frontDims
        ZoomPercent=100
        ZoomLabel=$zoomLabel
        Mode='Buttons'
        ModeButton=$mode
        DragWhich=''
        Project=$project
        Ship=$ship
        Fandom=$fandom
        Tags=$tags
        CoverType=$coverType
        SaveButton=$save
        RemoveButton=$remove
        Status=$status
        Saved=$false
    }

    foreach($control in @($card,$viewport,$picture,$zoomOut,$zoomIn,$fit,$mode,$leftNum,$rightNum,$auto,$center,$save,$remove)){
        $control.Tag=$state
    }

    $pair=$null
    try{$pair=Get-AutoSplit $bitmap}catch{}
    if($null -ne $pair -and @($pair).Count -ge 2){
        $left=[int]$pair[0]
        $right=[int]$pair[1]
    }else{
        $mid=[int][math]::Round($bitmap.Width/2.0)
        $half=[int][math]::Max(2,[math]::Round($bitmap.Width*0.04))
        $left=$mid-$half
        $right=$mid+$half
    }
    $left=[math]::Max(1,[math]::Min($bitmap.Width-2,$left))
    $right=[math]::Max($left+1,[math]::Min($bitmap.Width-1,$right))
    $leftNum.Value=[decimal]$left
    $rightNum.Value=[decimal]$right

    $picture.Add_Paint({param($sender,$e) Draw-LibraryScrollGuides $sender $e})
    $picture.Add_MouseEnter({param($sender,$e) try{$sender.Focus()}catch{}})
    $picture.Add_MouseWheel({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st){return}
        if(([Windows.Forms.Control]::ModifierKeys -band [Windows.Forms.Keys]::Control) -eq [Windows.Forms.Keys]::Control){
            if($e.Delta -gt 0){Set-LibraryScrollZoom $st ($st.ZoomPercent+25)}else{Set-LibraryScrollZoom $st ($st.ZoomPercent-25)}
            if($null -ne $e.PSObject.Properties['Handled']){$e.Handled=$true}
        }
    })
    $picture.Add_MouseDown({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st -or $st.Mode -ne 'Drag'){return}
        $w=[math]::Max(1,$sender.ClientSize.Width)
        $lx=([int]$st.LeftNum.Value/[double]$st.Bitmap.Width)*$w
        $rx=([int]$st.RightNum.Value/[double]$st.Bitmap.Width)*$w
        $st.DragWhich=''
        if([math]::Abs($e.X-$lx) -le [math]::Abs($e.X-$rx)){
            if([math]::Abs($e.X-$lx) -le 20){$st.DragWhich='Left'}
        }else{
            if([math]::Abs($e.X-$rx) -le 20){$st.DragWhich='Right'}
        }
    })
    $picture.Add_MouseMove({
        param($sender,$e)
        $st=$sender.Tag
        if($null -eq $st -or $st.Mode -ne 'Drag' -or [string]::IsNullOrEmpty([string]$st.DragWhich)){return}
        Set-LibraryScrollGuideAt $st $st.DragWhich $e.X
    })
    $picture.Add_MouseUp({param($sender,$e) $st=$sender.Tag;if($null -ne $st){$st.DragWhich=''}})
    $picture.Add_MouseLeave({param($sender,$e) $st=$sender.Tag;if($null -ne $st){$st.DragWhich=''}})

    $viewport.Add_Resize({param($sender,$e) $st=$sender.Tag;if($null -ne $st){Update-LibraryScrollZoom $st}})
    $zoomOut.Add_Click({param($sender,$e) $st=$sender.Tag;Set-LibraryScrollZoom $st ($st.ZoomPercent-25)})
    $zoomIn.Add_Click({param($sender,$e) $st=$sender.Tag;Set-LibraryScrollZoom $st ($st.ZoomPercent+25)})
    $fit.Add_Click({param($sender,$e) $st=$sender.Tag;Set-LibraryScrollZoom $st 100})
    $mode.Add_Click({
        param($sender,$e)
        $st=$sender.Tag
        if($st.Mode -eq 'Drag'){Set-LibraryScrollMode $st 'Buttons'}else{Set-LibraryScrollMode $st 'Drag'}
    })
    $leftNum.Add_ValueChanged({param($sender,$e) $st=$sender.Tag;Update-LibraryScrollState $st})
    $rightNum.Add_ValueChanged({param($sender,$e) $st=$sender.Tag;Update-LibraryScrollState $st})
    $auto.Add_Click({
        param($sender,$e)
        $st=$sender.Tag
        try{$p=Get-AutoSplit $st.Bitmap}catch{$p=$null}
        if($null -ne $p -and @($p).Count -ge 2){
            $l=[math]::Max(1,[math]::Min($st.Bitmap.Width-2,[int]$p[0]))
            $r=[math]::Max($l+1,[math]::Min($st.Bitmap.Width-1,[int]$p[1]))
            $st.LeftNum.Value=[decimal]$l
            $st.RightNum.Value=[decimal]$r
        }
    })
    $center.Add_Click({
        param($sender,$e)
        $st=$sender.Tag
        $mid=[int][math]::Round($st.Bitmap.Width/2.0)
        $half=[int][math]::Max(2,[math]::Round($st.Bitmap.Width*0.04))
        $l=[math]::Max(1,$mid-$half)
        $r=[math]::Min($st.Bitmap.Width-1,$mid+$half)
        $st.LeftNum.Value=[decimal]$l
        $st.RightNum.Value=[decimal]$r
    })
    $save.Add_Click({
        param($sender,$e)
        $st=$sender.Tag
        try{Save-LibraryScrollCard $st}catch{Show-Error ('This cover could not be saved.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message)}
    })
    $remove.Add_Click({
        param($sender,$e)
        $st=$sender.Tag
        if($null -ne $st){Remove-LibraryScrollCard $st}
    })

    Update-LibraryScrollState $state
    Set-LibraryScrollMode $state 'Buttons'
    Update-LibraryScrollZoom $state
    return $state
}

function Hide-LibraryRegularSplitterForMulti {
    $script:LibraryRegularVisibility=@()
    foreach($control in @($tabSplit.Controls)){
        if($control -eq $panelWrapDrop){continue}
        if($null -ne $script:LibraryMultiScrollHost -and $control -eq $script:LibraryMultiScrollHost){continue}
        if($control.Top -ge 190){
            $script:LibraryRegularVisibility += [pscustomobject]@{Control=$control;Visible=$control.Visible}
            $control.Visible=$false
        }
    }
}

function Restore-LibraryRegularSplitter {
    foreach($entry in @($script:LibraryRegularVisibility)){
        try{
            if($null -ne $entry.Control -and -not $entry.Control.IsDisposed){$entry.Control.Visible=[bool]$entry.Visible}
        }catch{}
    }
    $script:LibraryRegularVisibility=@()
    if($null -ne $btnChooseWrap){$btnChooseWrap.Visible=$false}
}

function Relayout-LibraryMultiScroll {
    if($null -eq $script:LibraryMultiScrollHost){return}
    $y=0
    $ordinal=0
    $total=@($script:LibraryMultiScrollStates).Count
    foreach($st in @($script:LibraryMultiScrollStates)){
        if($null -eq $st -or $null -eq $st.Card -or $st.Card.IsDisposed){continue}
        $ordinal++
        $st.Card.Location=New-Object Drawing.Point(0,$y)
        $header=@($st.Card.Controls|Where-Object{$_ -is [Windows.Forms.Label]})|Select-Object -First 1
        if($null -ne $header){$header.Text=("COVER {0} OF {1}  -  {2}" -f $ordinal,$total,[IO.Path]::GetFileName($st.Path))}
        $y += $st.Card.Height+18
    }
    $script:LibraryMultiScrollHost.Height=[math]::Max(100,$y)
    $tabSplit.AutoScrollMinSize=New-Object Drawing.Size(1180,($script:LibraryMultiScrollHost.Top+$script:LibraryMultiScrollHost.Height+80))
}

function Remove-LibraryScrollCard($State){
    if($null -eq $State){return}
    try{
        if($null -ne $State.Picture){$State.Picture.Image=$null}
        if($null -ne $State.Bitmap){$State.Bitmap.Dispose();$State.Bitmap=$null}
    }catch{}
    try{
        if($null -ne $State.Card -and $null -ne $State.Card.Parent){$State.Card.Parent.Controls.Remove($State.Card)}
        if($null -ne $State.Card){$State.Card.Dispose()}
    }catch{}

    $script:LibraryMultiScrollStates=@($script:LibraryMultiScrollStates|Where-Object{$_ -ne $State})
    if(@($script:LibraryMultiScrollStates).Count -eq 0){
        Close-LibraryMultiWrapScroll $true
    }else{
        Relayout-LibraryMultiScroll
    }
}

function Close-LibraryMultiWrapScroll([bool]$RestoreRegular=$true){
    if($null -ne $script:LibraryMultiScrollHost){
        foreach($st in @($script:LibraryMultiScrollStates)){
            try{
                if($null -ne $st.Picture){$st.Picture.Image=$null}
                if($null -ne $st.Bitmap){$st.Bitmap.Dispose();$st.Bitmap=$null}
            }catch{}
        }
        try{$tabSplit.Controls.Remove($script:LibraryMultiScrollHost);$script:LibraryMultiScrollHost.Dispose()}catch{}
    }
    $script:LibraryMultiScrollHost=$null
    $script:LibraryMultiScrollStates=@()
    $tabSplit.AutoScrollMinSize=New-Object Drawing.Size(1180,1460)
    if($RestoreRegular){Restore-LibraryRegularSplitter}
}

function Show-LibraryUnifiedWrapPaths([string[]]$Paths){
    $valid=@(
        $Paths | Where-Object {
            if([string]::IsNullOrWhiteSpace([string]$_)){return $false}
            if(-not(Test-Path -LiteralPath $_ -PathType Leaf)){return $false}
            $ext=[IO.Path]::GetExtension([string]$_).ToLowerInvariant()
            return $ext -in @('.png','.jpg','.jpeg','.bmp','.tif','.tiff')
        }
    )
    if($valid.Count -eq 0){Show-Info 'Drop image files only: PNG, JPG, BMP, TIF, or TIFF.';return}
    if($valid.Count -eq 1){
        Close-LibraryMultiWrapScroll $true
        Set-WrapDroppedFile $valid[0]
        return
    }

    Close-LibraryMultiWrapScroll $true
    Hide-LibraryRegularSplitterForMulti

    $multiHost=New-Object Windows.Forms.Panel
    $multiHost.Name='LibraryMultiScrollHost'
    $multiHost.Location=New-Object Drawing.Point(18,224)
    $multiHost.Size=New-Object Drawing.Size(1145,100)
    $multiHost.BackColor=[Drawing.Color]::FromArgb(38,14,56)
    $script:LibraryMultiScrollHost=$multiHost
    $tabSplit.Controls.Add($multiHost)

    $states=@()
    $failures=@()
    $ordinal=0
    foreach($path in $valid){
        try{
            $ordinal++
            $state=New-LibraryScrollCard $path $ordinal $valid.Count
            $states += $state
            $multiHost.Controls.Add($state.Card)
        }catch{
            $failures += ([IO.Path]::GetFileName($path)+': '+$_.Exception.Message)
        }
    }
    $script:LibraryMultiScrollStates=@($states)

    if($states.Count -eq 0){
        Close-LibraryMultiWrapScroll $true
        $detail=if($failures.Count -gt 0){[Environment]::NewLine+[Environment]::NewLine+($failures -join [Environment]::NewLine)}else{''}
        Show-Error ('None of those files could be opened as cover images.'+$detail)
        return
    }

    Relayout-LibraryMultiScroll
    $tabSplit.AutoScrollPosition=New-Object Drawing.Point(0,0)
    $multiHost.BringToFront()

    if($failures.Count -gt 0){
        Show-Info ("Some covers could not be opened: $($failures.Count)"+[Environment]::NewLine+[Environment]::NewLine+($failures -join [Environment]::NewLine))
    }
}

function Update-LibraryRegularZoomLayout {
    if($null -eq $script:RegularWrapViewport -or $null -eq $pbWrapPreview){return}
    if($null -eq $script:WrapBitmap -or $null -eq $pbWrapPreview.Image){
        $pbWrapPreview.Size=New-Object Drawing.Size([math]::Max(1,$script:RegularWrapViewport.ClientSize.Width-4),[math]::Max(1,$script:RegularWrapViewport.ClientSize.Height-4))
        $pbWrapPreview.Location=New-Object Drawing.Point(0,0)
        return
    }
    $vw=[math]::Max(40,$script:RegularWrapViewport.ClientSize.Width-4)
    $vh=[math]::Max(40,$script:RegularWrapViewport.ClientSize.Height-4)
    $fit=[math]::Min($vw/[double]$script:WrapBitmap.Width,$vh/[double]$script:WrapBitmap.Height)
    if($fit -le 0){$fit=1.0}
    $zoom=[math]::Max(50,[math]::Min(400,[int]$script:RegularWrapZoomPercent))
    $script:RegularWrapZoomPercent=$zoom
    $scale=$fit*($zoom/100.0)
    $w=[math]::Max(1,[int][math]::Round($script:WrapBitmap.Width*$scale))
    $h=[math]::Max(1,[int][math]::Round($script:WrapBitmap.Height*$scale))
    $pbWrapPreview.Size=New-Object Drawing.Size($w,$h)
    $x=if($w -lt $vw){[int](($vw-$w)/2)}else{0}
    $y=if($h -lt $vh){[int](($vh-$h)/2)}else{0}
    $pbWrapPreview.Location=New-Object Drawing.Point($x,$y)
    if($null -ne $script:RegularZoomLabel){$script:RegularZoomLabel.Text=([string]$zoom+'%')}
    $pbWrapPreview.Invalidate()
}

function Set-LibraryRegularZoom([int]$Percent){
    $script:RegularWrapZoomPercent=[math]::Max(50,[math]::Min(400,$Percent))
    Update-LibraryRegularZoomLayout
}

function Set-LibraryRegularSplitMode([string]$Mode){
    if($Mode -eq 'Drag'){
        $script:RegularSplitMode='Drag'
        $script:RegularSplitDragWhich=''
        $numSplitLeft.Enabled=$false
        $numSplitRight.Enabled=$false
        $pbWrapPreview.Cursor=[Windows.Forms.Cursors]::VSplit
        if($null -ne $script:RegularModeButton){$script:RegularModeButton.Text='MODE: DRAG LINES'}
    }else{
        $script:RegularSplitMode='Buttons'
        $script:RegularSplitDragWhich=''
        $numSplitLeft.Enabled=$true
        $numSplitRight.Enabled=$true
        $pbWrapPreview.Cursor=[Windows.Forms.Cursors]::Default
        if($null -ne $script:RegularModeButton){$script:RegularModeButton.Text='MODE: BUTTONS'}
    }
    $pbWrapPreview.Invalidate()
}

function Set-LibraryRegularGuideAt([string]$Which,[int]$MouseX){
    if($null -eq $script:WrapBitmap -or $null -eq $pbWrapPreview){return}
    $pw=[math]::Max(1,$pbWrapPreview.ClientSize.Width)
    $px=[int][math]::Round(($MouseX/[double]$pw)*$script:WrapBitmap.Width)
    $px=[math]::Max(1,[math]::Min($script:WrapBitmap.Width-1,$px))
    if($Which -eq 'Left'){
        $px=[math]::Min($px,[int]$numSplitRight.Value-1)
        $numSplitLeft.Value=[decimal][math]::Max([int]$numSplitLeft.Minimum,[math]::Min([int]$numSplitLeft.Maximum,$px))
    }elseif($Which -eq 'Right'){
        $px=[math]::Max($px,[int]$numSplitLeft.Value+1)
        $numSplitRight.Value=[decimal][math]::Max([int]$numSplitRight.Minimum,[math]::Min([int]$numSplitRight.Maximum,$px))
    }
}

function Draw-SplitGuides($sender,$e){
    if($null -eq $script:WrapBitmap -or $null -eq $pbWrapPreview.Image -or $null -eq $e -or $null -eq $e.Graphics){return}
    $w=[math]::Max(1,$sender.ClientSize.Width)
    $h=[math]::Max(1,$sender.ClientSize.Height)
    $lx=($script:SplitLeft/[double]$script:WrapBitmap.Width)*$w
    $rx=($script:SplitRight/[double]$script:WrapBitmap.Width)*$w
    $color=if($script:RegularSplitMode -eq 'Drag'){[Drawing.Color]::FromArgb(255,220,90)}else{[Drawing.Color]::White}
    $pen=New-Object Drawing.Pen($color,3)
    try{
        $pen.DashStyle=[Drawing.Drawing2D.DashStyle]::Dash
        $e.Graphics.DrawLine($pen,[float]$lx,0,[float]$lx,[float]$h)
        $e.Graphics.DrawLine($pen,[float]$rx,0,[float]$rx,[float]$h)
    }finally{$pen.Dispose()}
}

function Save-WrapAndPieces {
    if($null -eq $script:WrapBitmap -or [string]::IsNullOrWhiteSpace([string]$script:SelectedWrapFile)){
        Show-Info 'Drop a full cover wrap first.'
        return
    }
    Update-SplitPreview
    if($script:SplitLeft -le 0 -or $script:SplitRight -le $script:SplitLeft -or $script:SplitRight -ge $script:WrapBitmap.Width){
        Show-Error 'The split guide positions are invalid.'
        return
    }

    try{
        $sourcePath=[string]$script:SelectedWrapFile
        $base=[IO.Path]::GetFileNameWithoutExtension($sourcePath)
        $pieces=@(
            @{Position='Back Cover';X=0;Width=[int]$script:SplitLeft;Label='Back Cover'},
            @{Position='Spine';X=[int]$script:SplitLeft;Width=[int]($script:SplitRight-$script:SplitLeft);Label='Spine'},
            @{Position='Front Cover';X=[int]$script:SplitRight;Width=[int]($script:WrapBitmap.Width-$script:SplitRight);Label='Front Cover'}
        )

        $created=@()
        try{
            foreach($piece in $pieces){
                $stored=Make-UniqueStoredName '.png'
                $dest=Join-Path $script:FilesRoot $stored
                Save-CropPng $script:WrapBitmap ([int]$piece.X) ([int]$piece.Width) $dest
                $created += $dest
                $script:PendingCoverType=[string]$cmbWrapCoverType.Text
                $recordArgs=@{
                    OriginalName=(Make-SplitName $base $piece.Label)
                    StoredName=$stored
                    Position=$piece.Position
                    Project=$txtWrapProject.Text
                    Ship=$txtWrapShip.Text
                    Fandom=$txtWrapFandom.Text
                    Tags=$txtWrapTags.Text
                }
                Add-LibraryRecord @recordArgs | Out-Null
            }
        }catch{
            foreach($file in @($created)){try{Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue}catch{}}
            throw
        }

        if($null -ne $chkMoveWrap -and $chkMoveWrap.Checked){
            try{Remove-Item -LiteralPath $sourcePath -Force -ErrorAction Stop}catch{}
        }

        Refresh-HierarchyTree
        Refresh-LibraryGrid

        $script:SelectedWrapFile=$null
        if($null -ne $lblWrapFile){$lblWrapFile.Text='No full wrap selected'}
        if($null -ne $script:WrapBitmap){try{$script:WrapBitmap.Dispose()}catch{};$script:WrapBitmap=$null}
        Set-PictureImage $pbWrapPreview $null
        Set-PictureImage $pbBackPreview $null
        Set-PictureImage $pbSpinePreview $null
        Set-PictureImage $pbFrontPreview $null
        $txtWrapProject.Clear()
        $txtWrapShip.Clear()
        $txtWrapFandom.Clear()
        $txtWrapTags.Clear()
        Show-Info 'Saved Back Cover, Spine, and Front Cover.'
    }catch{
        Show-Error ('The full wrap could not be split and saved.'+[Environment]::NewLine+[Environment]::NewLine+$_.Exception.Message)
    }
}

function Initialize-LibraryRegularZoom {
    if($null -eq $pbWrapPreview -or $null -eq $tabSplit){return}
    if($null -ne $script:RegularWrapViewport -and -not $script:RegularWrapViewport.IsDisposed){return}

    $bounds=$pbWrapPreview.Bounds
    try{$tabSplit.Controls.Remove($pbWrapPreview)}catch{}

    $viewport=New-Object Windows.Forms.Panel
    $viewport.Name='RegularWrapZoomViewport'
    $viewport.Bounds=$bounds
    $viewport.Anchor='Top,Left,Right'
    $viewport.AutoScroll=$true
    $viewport.BackColor=[Drawing.Color]::FromArgb(38,14,56)
    $viewport.BorderStyle='FixedSingle'
    $tabSplit.Controls.Add($viewport)
    $viewport.Controls.Add($pbWrapPreview)
    $pbWrapPreview.Location=New-Object Drawing.Point(0,0)
    $pbWrapPreview.SizeMode='StretchImage'
    $pbWrapPreview.BorderStyle='None'
    $pbWrapPreview.TabStop=$true
    $script:RegularWrapViewport=$viewport

    $zoomOut=New-Object Windows.Forms.Button
    $zoomOut.Name='RegularWrapZoomOut'
    $zoomOut.Text='−'
    $zoomOut.Location=New-Object Drawing.Point(730,602)
    $zoomOut.Size=New-Object Drawing.Size(40,29)
    $tabSplit.Controls.Add($zoomOut)

    $zoomLabel=New-LibraryScrollLabel '100%' 775 606 55 22
    $zoomLabel.TextAlign='MiddleCenter'
    $tabSplit.Controls.Add($zoomLabel)
    $script:RegularZoomLabel=$zoomLabel

    $zoomIn=New-Object Windows.Forms.Button
    $zoomIn.Name='RegularWrapZoomIn'
    $zoomIn.Text='+'
    $zoomIn.Location=New-Object Drawing.Point(835,602)
    $zoomIn.Size=New-Object Drawing.Size(40,29)
    $tabSplit.Controls.Add($zoomIn)

    $fit=New-Object Windows.Forms.Button
    $fit.Name='RegularWrapZoomFit'
    $fit.Text='FIT'
    $fit.Location=New-Object Drawing.Point(882,602)
    $fit.Size=New-Object Drawing.Size(58,29)
    $tabSplit.Controls.Add($fit)

    $mode=New-Object Windows.Forms.Button
    $mode.Name='RegularWrapSplitMode'
    $mode.Text='MODE: BUTTONS'
    $mode.Location=New-Object Drawing.Point(950,602)
    $mode.Size=New-Object Drawing.Size(185,29)
    $tabSplit.Controls.Add($mode)
    $script:RegularModeButton=$mode

    $zoomOut.Add_Click({Set-LibraryRegularZoom ($script:RegularWrapZoomPercent-25)})
    $zoomIn.Add_Click({Set-LibraryRegularZoom ($script:RegularWrapZoomPercent+25)})
    $fit.Add_Click({Set-LibraryRegularZoom 100})
    $mode.Add_Click({
        if($script:RegularSplitMode -eq 'Drag'){Set-LibraryRegularSplitMode 'Buttons'}else{Set-LibraryRegularSplitMode 'Drag'}
    })

    $viewport.Add_Resize({Update-LibraryRegularZoomLayout})
    $pbWrapPreview.Add_MouseEnter({try{$pbWrapPreview.Focus()}catch{}})
    $pbWrapPreview.Add_MouseWheel({
        param($sender,$e)
        if(([Windows.Forms.Control]::ModifierKeys -band [Windows.Forms.Keys]::Control) -eq [Windows.Forms.Keys]::Control){
            if($e.Delta -gt 0){Set-LibraryRegularZoom ($script:RegularWrapZoomPercent+25)}else{Set-LibraryRegularZoom ($script:RegularWrapZoomPercent-25)}
            if($null -ne $e.PSObject.Properties['Handled']){$e.Handled=$true}
        }
    })
    $pbWrapPreview.Add_MouseDown({
        param($sender,$e)
        if($script:RegularSplitMode -ne 'Drag' -or $null -eq $script:WrapBitmap){return}
        $w=[math]::Max(1,$sender.ClientSize.Width)
        $lx=($script:SplitLeft/[double]$script:WrapBitmap.Width)*$w
        $rx=($script:SplitRight/[double]$script:WrapBitmap.Width)*$w
        $script:RegularSplitDragWhich=''
        if([math]::Abs($e.X-$lx) -le [math]::Abs($e.X-$rx)){
            if([math]::Abs($e.X-$lx) -le 20){$script:RegularSplitDragWhich='Left'}
        }else{
            if([math]::Abs($e.X-$rx) -le 20){$script:RegularSplitDragWhich='Right'}
        }
    })
    $pbWrapPreview.Add_MouseMove({
        param($sender,$e)
        if($script:RegularSplitMode -eq 'Drag' -and -not [string]::IsNullOrEmpty($script:RegularSplitDragWhich)){
            Set-LibraryRegularGuideAt $script:RegularSplitDragWhich $e.X
        }
    })
    $pbWrapPreview.Add_MouseUp({$script:RegularSplitDragWhich=''})
    $pbWrapPreview.Add_MouseLeave({$script:RegularSplitDragWhich=''})

    Set-LibraryRegularSplitMode 'Buttons'
    Update-LibraryRegularZoomLayout
}

function Initialize-LibraryBatchSplitDropIn {
    if($null -eq $tabSplit){throw 'The Split Full Cover tab is unavailable.'}

    foreach($control in @(Get-LibraryAllChildControls $tabSplit)){
        if($control -is [Windows.Forms.Button]){
            $upper=([string]$control.Text).Trim().ToUpperInvariant()
            if($upper -in @('ADD MULTIPLE FULL WRAPS','BATCH SPLIT WRAPS')){
                try{if($null -ne $control.Parent){$control.Parent.Controls.Remove($control)};$control.Dispose()}catch{}
            }
        }
    }

    if($null -ne $btnChooseWrap){$btnChooseWrap.Visible=$false}
    if($null -ne $lblWrapDrop){$lblWrapDrop.Text='DROP FULL COVER IMAGE(S) HERE'}
    if($null -ne $lblWrapDrop2){
        $lblWrapDrop2.Text='Select one or more covers in File Explorer and drag them into this purple box'
        $lblWrapDrop2.Width=760
    }

    if($null -ne $btnSaveSplit){$btnSaveSplit.Text='SAVE BACK + SPINE + FRONT'}
    if($null -ne $metaTitle){$metaTitle.Text='Tags for the 3 saved pieces'}
    if($null -ne $wrapStorageNote){
        $wrapStorageNote.Text='The full wrap is used only as the source image. The Library saves Back Cover, Spine, and Front Cover.'
    }
    if($null -ne $chkMoveWrap){
        $chkMoveWrap.Text='Remove original full-wrap file from File Explorer after saving pieces'
    }

    Initialize-LibraryRegularZoom

    $form.Add_FormClosed({
        foreach($st in @($script:LibraryMultiScrollStates)){
            try{if($null -ne $st.Bitmap){$st.Bitmap.Dispose();$st.Bitmap=$null}}catch{}
        }
    })
}
"""

patcher=r"""$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms

$appRoot=Split-Path -Parent $PSScriptRoot
$backupDir=Join-Path $appRoot 'UpdateBackup'
$backupMain=Join-Path $backupDir 'CoverVault.ps1'
$backupVersion=Join-Path $backupDir 'AppVersion.json'
$targetMain=Join-Path $PSScriptRoot 'CoverVault.ps1'
$targetVersion=Join-Path $PSScriptRoot 'AppVersion.json'
$dropIn=Join-Path $PSScriptRoot 'BatchSplitDropIn.ps1'
$launcher=Join-Path $PSScriptRoot 'Launch Cover Vault.vbs'

function Relaunch-App {
    if(Test-Path -LiteralPath $launcher){
        Start-Process -FilePath 'wscript.exe' -ArgumentList ('"' + $launcher + '"')
    }
}

try{
    if(-not(Test-Path -LiteralPath $backupMain)){throw 'The updater backup is missing the previous Library app script.'}
    if(-not(Test-Path -LiteralPath $dropIn)){throw 'The scroll splitter component is missing.'}

    $text=[IO.File]::ReadAllText($backupMain,[Text.Encoding]::UTF8)
    if(-not $text.Contains('function Register-CoverDropTarget')){throw 'Could not find The Library drag-and-drop handler.'}
    if(-not $text.Contains('Show-LibraryUnifiedWrapPaths -Paths $valid')){throw 'The multi-file drop route is missing.'}
    if(-not $text.Contains('Initialize-LibraryBatchSplitDropIn')){throw 'The drop-in startup hook is missing.'}

    $dropFunction=$text.IndexOf('function Register-CoverDropTarget')
    $singleNeedle='Set-WrapDroppedFile $valid[0]'
    $singleCall=if($dropFunction -ge 0){$text.IndexOf($singleNeedle,$dropFunction)}else{-1}
    if($singleCall -ge 0){
        $before=$text.Substring([math]::Max(0,$singleCall-350),[math]::Min(350,$singleCall))
        if($before.Contains('if ($valid.Count -eq 1)') -and -not $before.Contains('Close-LibraryMultiWrapScroll')){
            $nl=[Environment]::NewLine
            $insert='if (Get-Command Close-LibraryMultiWrapScroll -ErrorAction SilentlyContinue) {'+$nl+
                    '                    Close-LibraryMultiWrapScroll $true'+$nl+
                    '                }'+$nl+
                    '                '
            $text=$text.Substring(0,$singleCall)+$insert+$text.Substring($singleCall)
        }
    }

    $wrapFunction=$text.IndexOf('function Set-WrapDroppedFile')
    $autoNeedle='Auto-DetectSplit'
    $autoCall=if($wrapFunction -ge 0){$text.IndexOf($autoNeedle,$wrapFunction)}else{-1}
    if($autoCall -ge 0){
        $lineEnd=$text.IndexOf([char]10,$autoCall)
        if($lineEnd -lt 0){$lineEnd=$text.Length}else{$lineEnd++}
        $nearEnd=[math]::Min($text.Length,$lineEnd+220)
        $afterAuto=$text.Substring($lineEnd,$nearEnd-$lineEnd)
        if(-not $afterAuto.Contains('Set-LibraryRegularZoom')){
            $nl=[Environment]::NewLine
            $zoomHook='        if (Get-Command Set-LibraryRegularZoom -ErrorAction SilentlyContinue) { Set-LibraryRegularZoom 100 }'+$nl
            $text=$text.Substring(0,$lineEnd)+$zoomHook+$text.Substring($lineEnd)
        }
    }

    [IO.File]::WriteAllText($targetMain,$text,(New-Object Text.UTF8Encoding($true)))

    @'
{
  "appId": "the-library",
  "appName": "The Library",
  "version": "1.0.18",
  "manifestUrl": "https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
}
'@ | Set-Content -LiteralPath $targetVersion -Encoding UTF8

    Relaunch-App
}
catch{
    $message=$_.Exception.Message
    try{if(Test-Path -LiteralPath $backupMain){Copy-Item -LiteralPath $backupMain -Destination $targetMain -Force}}catch{}
    try{if(Test-Path -LiteralPath $backupVersion){Copy-Item -LiteralPath $backupVersion -Destination $targetVersion -Force}}catch{}
    try{
        [Windows.Forms.MessageBox]::Show(
            ('The Library could not install the scroll splitter + zoom update.'+[Environment]::NewLine+[Environment]::NewLine+$message+[Environment]::NewLine+[Environment]::NewLine+'The previous app version was restored.'),
            'The Library Update'
        )|Out-Null
    }catch{}
    Relaunch-App
}
"""

appver=json.dumps({
    "appId":"the-library",
    "appName":"The Library",
    "version":VERSION,
    "manifestUrl":"https://raw.githubusercontent.com/VeyrStudio/DesktopAppUpdates/main/the-library/manifest.json"
},indent=2).encode()

files=[]
for path,data in [
    ("CoverVault.ps1",patcher.encode("utf-8-sig")),
    ("BatchSplitDropIn.ps1",dropin.encode("utf-8-sig")),
    ("AppVersion.json",appver),
]:
    files.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"contentBase64":base64.b64encode(data).decode("ascii")})

payload={"schemaVersion":1,"appId":"the-library","appName":"The Library","version":VERSION,"files":files,"delete":[]}
raw=json.dumps(payload,separators=(",",":")).encode()
name="payload-1.0.18-scroll-splitter-zoom.txt"
(TF/name).write_bytes(raw)
sha=hashlib.sha256(raw).hexdigest()

validation={
    "version":VERSION,
    "baseVersion":"1.0.17",
    "payload":name,
    "payloadSha256":sha,
    "requirements":{
        "scrollDownNotNext":"LibraryMultiScrollHost" in dropin and "LibraryWrapQueueNext" not in dropin,
        "saveWordingFixed":"SAVE BACK + SPINE + FRONT" in dropin,
        "zoom50To400":"Max(50" in dropin and "Min(400" in dropin,
        "fitButton":"Text='FIT'" in dropin,
        "ctrlWheelZoom":"ModifierKeys" in dropin and "MouseWheel" in dropin,
        "dragModeToggle":"MODE: DRAG LINES" in dropin and "MODE: BUTTONS" in dropin,
        "regularSplitterZoom":"Initialize-LibraryRegularZoom" in dropin,
        "multiSplitterZoom":"Update-LibraryScrollZoom" in dropin,
        "removesOldMultiButton":"ADD MULTIPLE FULL WRAPS" in dropin,
        "allInternalHashesVerified":all(hashlib.sha256(base64.b64decode(f["contentBase64"])).hexdigest()==f["sha256"] for f in files)
    }
}
if not all(validation["requirements"].values()):
    raise SystemExit(validation)

(TF/"scroll-splitter-zoom-1.0.18-validation.json").write_text(json.dumps(validation,indent=2),encoding="utf-8")
vd=ROOT/".library-v118-validation"
vd.mkdir(exist_ok=True)
for f in files:
    (vd/f["path"]).write_bytes(base64.b64decode(f["contentBase64"]))
print(json.dumps(validation,indent=2))
