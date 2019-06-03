param (
  [string]$drive,
  [switch]$h = $false
)
if ($h) {
  echo "usage: ec2 disk-by-drive-letter [-h] {drive}"
  echo ""
  echo "positional arguments:"
  echo "  drive  the drive to get disk info for"
  echo "optional arguments:"
  echo "  -h     show this help message and exit"
  exit 0
}
Get-WmiObject Win32_DiskDrive | % {
  $disk = $_
  $partitions = "ASSOCIATORS OF " +
                "{Win32_DiskDrive.DeviceID='$($disk.DeviceID)'} " +
                "WHERE AssocClass = Win32_DiskDriveToDiskPartition"
  Get-WmiObject -Query $partitions | % {
    $partition = $_
    $drives = "ASSOCIATORS OF " +
              "{Win32_DiskPartition.DeviceID='$($partition.DeviceID)'} " +
              "WHERE AssocClass = Win32_LogicalDiskToPartition"
    Get-WmiObject -Query $drives | % {
      New-Object -Type PSCustomObject -Property @{

        TargetId    = $disk.SCSITargetId
        DiskNumber  = $disk.Index
        DriveLetter = $_.DeviceID
      }
    }
  }
} | Where-Object DriveLetter -eq $drive | ConvertTo-Xml -As String
