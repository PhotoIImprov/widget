use widget;

DROP PROCEDURE IF EXISTS sp_clean_widget_db;
DELIMITER //
CREATE PROCEDURE `sp_clean_widget_db`()
BEGIN
  -- Empty out all the tables in the new widget database so we
  -- can start testing with a clean slate
  set @start_date = NOW();
  set @end_date = DATE_ADD(@start_date, INTERVAL 30 DAY);

  DELETE FROM pgresult;
  DELETE FROM pgasset;
  DELETE FROM campaign;
  DELETE FROM gameuser;
  DELETE FROM `client`;

  -- Now initialize with default client (image improv)
  INSERT INTO `client` (id, `name`, active) VALUES(1, 'ImageImprov', 1);
  INSERT INTO `campaign` (id, client_id, `name`, active, start_date, end_date) VALUES(1, 1, '1st Campaign', 1, @start_date, @end_date);

END //
DELIMITER ;

START TRANSACTION;

    CALL widget.sp_clean_widget_db();
    SELECT * from `client`;
    SELECT * from `campaign`;
ROLLBACK;
