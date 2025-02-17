-- Consulta para a versão do Oracle
SELECT version 
FROM PRODUCT_COMPONENT_VERSION 
WHERE product LIKE 'Oracle Database%';

-- Consulta para listar usuários ativos
SELECT username 
FROM dba_users 
WHERE account_status = 'OPEN' 
ORDER BY username;

-- Consulta para recursos do banco de dados
SELECT resource_name, current_utilization, max_utilization 
FROM v$resource_limit 
WHERE resource_name IN ('processes', 'sessions');

-- Consulta para o tamanho do banco de dados e espaço utilizado
SELECT 
  round(sum(used.bytes) / 1024 / 1024 / 1024) || ' GB' AS "Database Size",
  round(sum(used.bytes) / 1024 / 1024 / 1024) - 
  round(free.p / 1024 / 1024 / 1024) || ' GB' AS "Used space",
  round(free.p / 1024 / 1024 / 1024) || ' GB' AS "Free space"
FROM 
  (SELECT bytes FROM v$datafile
   UNION ALL
   SELECT bytes FROM v$tempfile
   UNION ALL
   SELECT bytes FROM v$log) used,
  (SELECT sum(bytes) AS p FROM dba_free_space) free
GROUP BY free.p;

-- Consulta para as 20 maiores tabelas
SELECT * 
FROM 
  (SELECT owner, segment_name AS table_name, bytes/1024/1024/1024 AS "SIZE (GB)"
   FROM dba_segments 
   WHERE segment_type = 'TABLE'
   AND segment_name NOT LIKE 'BIN%' 
   ORDER BY 3 DESC) 
WHERE rownum <= 20;

-- Consulta para top 10 queries mais lentas
SELECT rownum AS rank, a.* 
FROM 
  (SELECT elapsed_Time/1000000 AS elapsed_time, executions, cpu_time, sql_id, sql_text
   FROM v$sqlarea 
   WHERE elapsed_time/1000000 > 5 
   ORDER BY elapsed_time DESC) a 
WHERE rownum < 11;

-- Consulta para detalhes de backup do RMAN
SELECT
  TO_CHAR(j.start_time, 'yyyy-mm-dd hh24:mi:ss') AS start_time,
  TO_CHAR(j.end_time, 'yyyy-mm-dd hh24:mi:ss') AS end_time,
  (j.output_bytes/1024/1024) AS output_mbytes,
-- j.status, 
  j.input_type,
  DECODE(TO_CHAR(j.start_time, 'd'), 
         1, 'Sunday', 
         2, 'Monday', 
         3, 'Tuesday', 
         4, 'Wednesday', 
         5, 'Thursday', 
         6, 'Friday', 
         7, 'Saturday') AS dow,
  j.elapsed_seconds 
  -- j.time_taken_display,
  -- x.cf, 
  -- x.df, 
  -- x.i0, 
  -- x.i1, 
  -- x.l,
  ro.inst_id AS output_instance
FROM v$RMAN_BACKUP_JOB_DETAILS j
LEFT OUTER JOIN 
  (SELECT 
     d.session_recid, 
     d.session_stamp,
     SUM(CASE WHEN d.controlfile_included = 'YES' THEN d.pieces ELSE 0 END) AS CF,
     SUM(CASE WHEN d.controlfile_included = 'NO' AND d.backup_type||d.incremental_level = 'D' THEN d.pieces ELSE 0 END) AS DF,
     SUM(CASE WHEN d.backup_type||d.incremental_level = 'D0' THEN d.pieces ELSE 0 END) AS I0,
     SUM(CASE WHEN d.backup_type||d.incremental_level = 'I1' THEN d.pieces ELSE 0 END) AS I1,
     SUM(CASE WHEN d.backup_type = 'L' THEN d.pieces ELSE 0 END) AS L
   FROM v$BACKUP_SET_DETAILS d
   JOIN v$BACKUP_SET s ON s.set_stamp = d.set_stamp AND s.set_count = d.set_count
   WHERE s.input_file_scan_only = 'NO'
   GROUP BY d.session_recid, d.session_stamp) x 
ON x.session_recid = j.session_recid AND x.session_stamp = j.session_stamp
LEFT OUTER JOIN 
  (SELECT o.session_recid, o.session_stamp, MIN(inst_id) AS inst_id
   FROM Gv$RMAN_OUTPUT o
   GROUP BY o.session_recid, o.session_stamp) ro 
ON ro.session_recid = j.session_recid AND ro.session_stamp = j.session_stamp
WHERE j.start_time > TRUNC(SYSDATE)-7
ORDER BY j.start_time;
