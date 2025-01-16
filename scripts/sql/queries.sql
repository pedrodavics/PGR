SELECT version FROM PRODUCT_COMPONENT_VERSION WHERE product LIKE 'Oracle Database%';

select username from dba_users where account_status='OPEN' order by username;

select resource_name, current_utilization, max_utilization from v$resource_limit where resource_name in ('processes','sessions');

select round(sum(used.bytes) / 1024 / 1024 / 1024) || ' GB' "Database Size",
       round(sum(used.bytes) / 1024 / 1024 / 1024) -
       round(free.p / 1024 / 1024 / 1024) || ' GB' "Used space",
       round(free.p / 1024 / 1024 / 1024) || ' GB' "Free space"
  from (select bytes
          from v$datafile
        union all
        select bytes
          from v$tempfile
        union all
        select bytes from v$log) used,
       (select sum(bytes) as p from dba_free_space) free
 group by free.p;

select * from (select owner, segment_name table_name, bytes/1024/1024/1024 "SIZE (GB)" 
from dba_segments where segment_type = 'TABLE'
and segment_name not like 'BIN%' order by 3 desc) where rownum <= 20;
 
select rownum as rank, a.*
from (
select elapsed_Time/1000000 elapsed_time,
executions,
buffer_gets,
disk_reads,
cpu_time
hash_value,
sql_text
from v$sqlarea
where elapsed_time/1000000 > 5
order by elapsed_time desc) a
where rownum < 11;

select
to_char(j.start_time, 'yyyy-mm-dd hh24:mi:ss') start_time,
to_char(j.end_time, 'yyyy-mm-dd hh24:mi:ss') end_time,
(j.output_bytes/1024/1024) output_mbytes, j.status, j.input_type,
decode(to_char(j.start_time, 'd'), 1, 'Sunday', 2, 'Monday',
3, 'Tuesday', 4, 'Wednesday',
5, 'Thursday', 6, 'Friday',
7, 'Saturday') dow,
j.elapsed_seconds, j.time_taken_display,
x.cf, x.df, x.i0, x.i1, x.l,
ro.inst_id output_instance
from v$RMAN_BACKUP_JOB_DETAILS j
left outer join (select
d.session_recid, d.session_stamp,
sum(case when d.controlfile_included = 'YES' then d.pieces else 0 end) CF,
sum(case when d.controlfile_included = 'NO'
and d.backup_type||d.incremental_level = 'D' then d.pieces else 0 end) DF,
sum(case when d.backup_type||d.incremental_level = 'D0' then d.pieces else 0 end) I0,
sum(case when d.backup_type||d.incremental_level = 'I1' then d.pieces else 0 end) I1,
sum(case when d.backup_type = 'L' then d.pieces else 0 end) L
from
v$BACKUP_SET_DETAILS d
join v$BACKUP_SET s on s.set_stamp = d.set_stamp and s.set_count = d.set_count
where s.input_file_scan_only = 'NO'
group by d.session_recid, d.session_stamp) x
on x.session_recid = j.session_recid and x.session_stamp = j.session_stamp
left outer join (select o.session_recid, o.session_stamp, min(inst_id) inst_id
from Gv$RMAN_OUTPUT o
group by o.session_recid, o.session_stamp)
ro on ro.session_recid = j.session_recid and ro.session_stamp = j.session_stamp
where j.start_time > trunc(sysdate)-7
order by j.start_time;