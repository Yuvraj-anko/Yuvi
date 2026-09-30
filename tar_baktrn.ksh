#!/bin/ksh
# @(#) $Workfile:   tar_baktrn.ksh  $ $Revision:   1.10  $
#######################################################################################################
# PROGRAM HEADER                                                                                      #
#######################################################################################################
#                                                                                                     #
# FILE:        tar_baktrn.ksh                                                                         #
# DESCRIPTION: This script will backup and truncate SDIPRDMST, SDIPRDUPC, SDIPRDSDI, SDIPRCMST and    #
#              SDIPRCHDR tables. Tables SDIPRDMST, SDIPRDSDI, SDIVALMST and SDIORGMST will backup     #
#              only non-SDI data. Daily tables are used for backups. If no week day is specified,     #
#              backup tables will be derived by CALDAYEE weekday.                                     #
# USAGE:       For up-to-date command line arguments see the f_PgmUsage() function.                   #
#                                                                                                     #
#######################################################################################################
#  MODIFICATION HISTORY                                                                               #
#-----------------------------------------------------------------------------------------------------#
#  DEVELOPER        DATE         DESCRIPTION                                                          #
#-----------------------------------------------------------------------------------------------------#
#  Khiralal Habib   15-05-2001   SDIPRCMST table will not be backed up or truncated (MA).             #
#                                Also changed error trapping attributes.                              #
#  Peter Korng      26-11-2001   Uncomments the SDIPRCMST table.                                      #
#  Rob Sowulewski   03-04-2002   Added backup & truncate for table SDIPRCHDR                          #
#  Khiralal Habib   12-04-2002   Backup SDIPRDUPC to SDIPRDUPC_BAK, which will last longer than a     #
#                                week and help us investigate the missing APNs problem.               #
#  Mark Rootes      29-02-2008   Added backup & truncate for table TAR_SDIPRCHDR                      #
#  Mark van der     08-01-2010   Backup SDIPRDUPC to TAR_SDIPRDUPC_BAK now and do this for all        #
#          Klooster              environments, not just production.                                   #
#  C Jayasuriya     01-12-2011   Added backup details for SDIVALMST as part of EP on EKB project      #
#  C Jayasuriya     02-12-2011   QA Changes                                                           #
#  C Jayasuriya     24-01-2012   Added backup details for SDIORGMST as part of EP on EKB project      #
#  Morgan Waldron   01-03-2012   Changed to backup/delete non-EKB data only. Re-wrote to standards    #
#  Cursor Agent     30-09-2026   Fix race: unique per-truncate SQL temp file (RC=92 missing file).    #
#                                                                                                     #
#######################################################################################################


###########################################################################################
#                                                                                         #
# Variable Definitions                                                                    #
#                                                                                         #
###########################################################################################

# Global Constants
#
GC_cPGM_NAME=$(basename ${0})
GC_cVALID_DAYS="SUN MON TUE WED THU FRI SAT"


#      Global Variables
g_cWeekday=""
g_iSqlTmpSeq=0


###########################################################################################
#                                                                                         #
# Function Definition                                                                     #
#                                                                                         #
###########################################################################################

###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_PgmUsage                                                               #
# DESCRIPTION:   This function will display the correct script usage                      #
# USAGE:         f_PgmUsage                                                               #
#                                                                                         #
###########################################################################################
function f_PgmUsage
{
    ${tscm_DbgEnter}

    # Start of Function Execution

    echo
    echo "Usage: ${GC_cPGM_NAME} [ -d ] [ -w <WEEKDAY> ]"
    echo "   -d     = Show all debug level detail logging too."
    echo "   -w     = Weekday table to backup to (Default: caldayee weekday)"
    echo

    tarf_ExitAndCleanUp ${TARGC_iRC_FAILURE}

    ${tarm_DbgReturn}
}


###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_ProcessArg                                                             #
# DESCRIPTION:   This function will process any and all parameters passed in to the script#
# USAGE:         f_ProcessArg "${@}"                                                      #
#                ${@}=all parameters being passed to f_ProcessArg                         #
#                                                                                         #
###########################################################################################
function f_ProcessArg
{
    ${tscm_DbgEnter}

    # Start of Function Execution

    #
    # Expect options in the standard way (with a '-' pre-pended).
    #
    # Note: Having a ':' as the first character in the allowed options string
    #        stops 'getopts' from outputting extra annoying messages and dying.
    #
    while getopts :dw: option
    do
       case ${option} in
       d) tarf_SetDbgMode ${TARGC_cTRUE}  # Enable debug mode.
          ;;
       w) g_cWeekday=$(echo ${OPTARG} | tr '[a-z]' '[A-Z]')
          #Check if the parameter is a valid date
          echo ${GC_cVALID_DAYS} | grep ${g_cWeekday} > /dev/null
          
          if [[ ${?} -eq ${TARGC_iRC_FAILURE} ]]
          then
              tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_ERR} "Error: ${g_cWeekday} is not a valid weekday"
              tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_ERR} "Valid days: ${GC_cVALID_DAYS}"
              tarf_ExitAndCleanUp ${TARGC_iRC_FAILURE}
          fi
          ;;
       *) if [[ "${option}" = ":" ]]
          then
              tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_ERR} "Missing argument for option '-${OPTARG}'."
          else
             #
             # Was help (usage) requested in the standard UNIX way?
             #
                case ${OPTARG} in
                h|\?)
                    ;;
                *)
                  tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_ERR} "Unknown option '-${OPTARG}'."
                    ;;
                esac
          fi
          f_PgmUsage
          ;;
       esac
    done

    #
    # Shift all the '-' arguments (that 'getopts' picked up) out of the way
    #
    shift ${OPTIND}-1

    #
    # Check for the existence of any other stray/required arguments.
    #
    for l_cArg in ${*}; do
        case ${l_cArg} in
        *)
            tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_ERR} "Unrecognised argument '${l_cArg}'"

            f_PgmUsage
            ;;
        esac
    done

    #Check if parameter was entered for weekday, else default to caldayee weekday
    if [[ -z ${g_cWeekday} ]]
    then
        tarf_RunAndCheckRC ${TARGC_cLOG_FTL} "g_cWeekday=$(tar_sql.ksh -s "SELECT to_char(caldat,'DY') FROM caldayee WHERE cal_type = 'M'")"
        tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "No option passed, defaulting weekday to ${g_cWeekday}"
    fi

    ${tarm_DbgReturn}
}


###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_TruncTable                                                             #
# DESCRIPTION:   Truncate a table                                                         #
# USAGE:         f_TruncTable <TABLE>                                                     #
#                <TABLE> - The table to be truncated                                      #
#                                                                                         #
###########################################################################################
function f_TruncTable
{
    ${tarm_DbgEnter}

    typeset l_cTable="${1}"
    #
    # Use a unique temp SQL file per truncate call. Reusing a single
    # /tmp/${GC_cPGM_NAME}_$$.sql path races with tar_sql.ksh async cleanup
    # of the previous truncate, causing RC=92 "Cannot find script file".
    #
    (( g_iSqlTmpSeq += 1 ))
    typeset l_cSQLTMP="/tmp/${GC_cPGM_NAME}_$$_${l_cTable}_${g_iSqlTmpSeq}.sql"

    if [[ -z ${l_cTable} ]]
    then
        tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_FTL} "Error: NULL table name passed to truncate"
    fi

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Starting truncate of table ${l_cTable}"

cat > ${l_cSQLTMP} << EOF

    DECLARE
        status_out     NUMBER;
        status_msg_out VARCHAR2(1000);
    BEGIN
        schema_management.truncate_table('${l_cTable}',status_out,status_msg_out);

        IF status_out <> 0 THEN
            RAISE_APPLICATION_ERROR(-20002, 'Error (' || TO_CHAR(status_out) || ') occurred trying to truncate table ${l_cTable}: ' || status_msg_out);
        END IF;
    END;
/
EOF

    if [[ ! -f ${l_cSQLTMP} ]]
    then
        tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_FTL} "Error: Failed to create SQL temp file ${l_cSQLTMP}"
    fi

    tarf_RunAndCheckRC ${TARGC_cLOG_FTL} 'tar_sql.ksh ${l_cSQLTMP}'

    tarf_RunAndCheckRC ${TARGC_cLOG_WRN} 'rm -f ${l_cSQLTMP}'

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Truncate of table ${l_cTable} - Done"

    ${tarm_DbgReturn}
}


###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_DelTable                                                               #
# DESCRIPTION:   Delete data from table where the data is not part of EKB                 #
# USAGE:         f_DelTable <TABLE>                                                       #
#                <TABLE> - The table to be deleted from                                   #
#                                                                                         #
###########################################################################################
function f_DelTable
{
    ${tarm_DbgEnter}

    typeset l_cTable="${1}"

    if [[ -z ${l_cTable} ]]
    then
        tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_FTL} "Error: NULL table name passed to delete"
    fi

    typeset l_cSQL="DELETE FROM ${l_cTable} \
                    WHERE iss_tech_key NOT IN (SELECT pos_tech_key \
                                               FROM  sdiposee pos \
                                               WHERE  pos.pos_config_name = 'EKB' \
                                              )"

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Starting delete from table ${l_cTable}"

    tarf_RunAndCheckRC ${TARGC_cLOG_FTL} 'tar_sql.ksh -s "${l_cSQL}"'

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Delete from table ${l_cTable} - Done"

    ${tarm_DbgReturn}
}


###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_BackupTable                                                            #
# DESCRIPTION:   Backup table into appropiate ${g_cWeekday} table                         #
# USAGE:         f_BackupTable <TABLE> <BACKUP_TABLE>                                     #
#                <TABLE> - The table to be backed up                                      #
#                <BACKUP_TABLE> - Table to backup to.                                     #
#                                                                                         #
###########################################################################################
function f_BackupTable
{
    ${tarm_DbgEnter}

    typeset l_cTable="${1}"
    typeset l_cBackupTable="${2}"

    if [[ -z ${l_cTable} ]] || [[ -z ${l_cBackupTable} ]]
    then
        tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_FTL} "Error: NULL table name passed to backup"
    fi

    typeset l_cSQL="INSERT INTO ${l_cBackupTable} SELECT * FROM ${l_cTable}"

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Starting backup of table ${l_cTable} into ${l_cBackupTable}"

    tarf_RunAndCheckRC ${TARGC_cLOG_FTL} 'tar_sql.ksh -s "${l_cSQL}"'

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Backup of table ${l_cTable} - Done"

    ${tarm_DbgReturn}
}


###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_BackupTableNotEKB                                                      #
# DESCRIPTION:   Backup table into appropiate ${g_cWeekday} table where the data is not   #
#                part of EKB                                                              #
# USAGE:         f_BackupTableNotEKB <TABLE> <BACKUP_TABLE> <AND_COND>                    #
#                <TABLE> - The table to be backed up                                      #
#                <BACKUP_TABLE> - Table to backup to.                                     #
#                                                                                         #
###########################################################################################
function f_BackupTableNotEKB
{
    ${tarm_DbgEnter}

    typeset l_cTable="${1}"
    typeset l_cBackupTable="${2}"

    if [[ -z ${l_cTable} ]] || [[ -z ${l_cBackupTable} ]]
    then
        tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_FTL} "Error: NULL table name passed to backup"
    fi

    typeset l_cSQL="INSERT INTO ${l_cBackupTable} \
                    SELECT * FROM ${l_cTable} \
                    WHERE iss_tech_key NOT IN (SELECT pos_tech_key \
                                               FROM  sdiposee pos \
                                               WHERE  pos.pos_config_name = 'EKB' \
                                              )"

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Starting backup of table ${l_cTable} into ${l_cBackupTable}"

    tarf_RunAndCheckRC ${TARGC_cLOG_FTL} 'tar_sql.ksh -s "${l_cSQL}"'

    tarf_LogMsg "${l_cFuncName}" ${TARGC_cLOG_INF} "Backup of table ${l_cTable} - Done"

    ${tarm_DbgReturn}
}


###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_UserCleanUp                                                            #
# DESCRIPTION:   This function is entirely otional.                                       #
#                  This function should perform any script specific cleanup.              #
#                If present, tarf_ExitAndCleanup() will automatically detect, and call it #
#                The return code from this function will become the final exit code for   #
#                this script.                                                             #
# USAGE:         f_UserCleanup <P_IEXITCODE>                                              #
#                <P_IEXITCODE> - script exit code as passed to tarf_ExitAndCleanup()      #
#                                                                                         #
###########################################################################################
function f_UserCleanUp
{
    ${tarm_DbgEnter}

    typeset -i p_iExitCode=${1}

    tarf_RunAndCheckRC ${TARGC_cLOG_WRN} 'rm -f /tmp/${GC_cPGM_NAME}*'

    ${tarm_DbgReturn} ${p_iExitCode}
}


###########################################################################################
#                                                                                         #
# FUNCTION NAME: f_Main                                                                   #
# DESCRIPTION:   Main processing driver routine                                           #
# USAGE:         f_Main                                                                   #
#                                                                                         #
###########################################################################################
function f_Main
{
    ${tarm_DbgEnter}

    #Truncate daily tables
    f_TruncTable "SDIPRDMST_${g_cWeekday}"
    f_TruncTable "SDIPRDUPC_${g_cWeekday}"
    f_TruncTable "SDIPRDSDI_${g_cWeekday}"
    f_TruncTable "SDIPRCMST_${g_cWeekday}"
    f_TruncTable "SDIPRCHDR_${g_cWeekday}"
    f_TruncTable "SDIORGMST_${g_cWeekday}"
    f_TruncTable "SDIVALMST_${g_cWeekday}"


    #Backup tables
    f_BackupTable "SDIPRDUPC" "SDIPRDUPC_${g_cWeekday}"
    f_BackupTable "SDIPRDUPC" "TAR_SDIPRDUPC_BAK"
    f_BackupTable "SDIPRCMST" "SDIPRCMST_${g_cWeekday}"
    f_BackupTable "SDIPRCHDR" "SDIPRCHDR_${g_cWeekday}"
    f_BackupTable "TAR_SDIPRCHDR" "ARC_TAR_SDIPRCHDR_${g_cWeekday}"

    #Backup tables, excluding EKB data
    f_BackupTableNotEKB "SDIPRDMST" "SDIPRDMST_${g_cWeekday}"
    f_BackupTableNotEKB "SDIPRDSDI" "SDIPRDSDI_${g_cWeekday}"
    f_BackupTableNotEKB "SDIVALMST" "SDIVALMST_${g_cWeekday}"
    f_BackupTableNotEKB "SDIORGMST" "SDIORGMST_${g_cWeekday}"


    #Truncate work tables
    f_TruncTable "SDIPRDUPC"
    f_TruncTable "SDIPRCMST"
    f_TruncTable "SDIPRCHDR"
    f_TruncTable "TAR_SDIPRCHDR"


    #Delete the data from the work tables that is not part of EKB
    f_DelTable "SDIDNLEE"
    f_DelTable "SDIPRDMST"
    f_DelTable "SDIPRDSDI"
    f_DelTable "SDIORGMST"

    ${tarm_DbgReturn}
}


#############################################################################
#   Target Functional Library
#############################################################################
. tar_LibFunc.ksh

if [ ${?} -ne 0 ]; then
   echo "Error loading tar_LibFunc.ksh"
   exit 1
fi

####################################################################################################
#
#                 Start of Program Execution
#
####################################################################################################

tarf_Start "${*}"

f_ProcessArg "${@}"

f_Main

tarf_Finish
