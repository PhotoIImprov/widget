use widget;

DROP PROCEDURE IF EXISTS sp_clean_widget_db;
DELIMITER //
CREATE PROCEDURE `sp_clean_widget_db`()
BEGIN
  -- Empty out all the tables in the new widget database so we
  -- can start testing with a clean slate
  
  DELETE FROM pgresult;
  DELETE FROM pgasset;
  DELETE FROM campaign;
  DELETE FROM gameuser;
  DELETE FROM `client`;
  
END //
DELIMITER ;

START TRANSACTION;

    CALL widget.sp_clean_widget_db();
    
ROLLBACK;
