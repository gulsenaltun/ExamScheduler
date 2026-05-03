CREATE TABLE Bolum (
    bolum_id INT PRIMARY KEY IDENTITY(1,1),
    bolum_adi NVARCHAR(100) NOT NULL
);

CREATE TABLE Ders (
    ders_id INT PRIMARY KEY IDENTITY(1,1),
    ders_adi NVARCHAR(100) NOT NULL,
    ogrenci_sayisi INT NOT NULL,
    yariyil INT NOT NULL,
    bolum_id INT,
    FOREIGN KEY (bolum_id) REFERENCES Bolum(bolum_id)
);

CREATE TABLE Oturum (
    oturum_id INT PRIMARY KEY IDENTITY(1,1),
    aciklama NVARCHAR(50),
    baslangic_saat TIME,
    bitis_saat TIME
);

CREATE TABLE Derslik (
    derslik_id INT PRIMARY KEY IDENTITY(1,1),
    ad NVARCHAR(50),
    kapasite INT NOT NULL,
    tip NVARCHAR(20),
    aktif_mi BIT
);

CREATE TABLE Sinav (
    sinav_id INT PRIMARY KEY IDENTITY(1,1),
    ders_id INT,
    tarih DATE,
    oturum_id INT,
    FOREIGN KEY (ders_id) REFERENCES Ders(ders_id),
    FOREIGN KEY (oturum_id) REFERENCES Oturum(oturum_id)
);

CREATE TABLE Sinav_Salon (
    id INT PRIMARY KEY IDENTITY(1,1),
    sinav_id INT,
    derslik_id INT,
    FOREIGN KEY (sinav_id) REFERENCES Sinav(sinav_id),
    FOREIGN KEY (derslik_id) REFERENCES Derslik(derslik_id)
);


CREATE TABLE Personel (
    personel_id INT PRIMARY KEY IDENTITY(1,1),
    ad NVARCHAR(50),
    soyad NVARCHAR(50),
    unvan NVARCHAR(50),
    bolum_id INT,
    FOREIGN KEY (bolum_id) REFERENCES Bolum(bolum_id)
);

CREATE TABLE Gozetmen_Atama (
    atama_id INT PRIMARY KEY IDENTITY(1,1),
    sinav_id INT,
    personel_id INT,
    FOREIGN KEY (sinav_id) REFERENCES Sinav(sinav_id),
    FOREIGN KEY (personel_id) REFERENCES Personel(personel_id)
);

CREATE TABLE Personel_Durum (
    durum_id INT PRIMARY KEY IDENTITY(1,1),
    personel_id INT,
    tarih DATE,
    uygun_mu BIT,
    mazeret_turu NVARCHAR(100),
    FOREIGN KEY (personel_id) REFERENCES Personel(personel_id)
);


CREATE TRIGGER trg_Salon_Cakismaz
ON Sinav_Salon
INSTEAD OF INSERT
AS
BEGIN
    IF EXISTS (
        SELECT 1
        FROM Sinav_Salon ss
        JOIN Sinav s1 ON ss.sinav_id = s1.sinav_id
        JOIN Sinav s2 ON s2.sinav_id IN (SELECT sinav_id FROM inserted)
        WHERE ss.derslik_id IN (SELECT derslik_id FROM inserted)
        AND s1.tarih = s2.tarih
        AND s1.oturum_id = s2.oturum_id
    )
    BEGIN
        RAISERROR ('Bu derslikte aynı saat aralığında başka bir sınav var!', 16, 1);
        ROLLBACK;
    END
    ELSE
    BEGIN
        INSERT INTO Sinav_Salon (sinav_id, derslik_id)
        SELECT sinav_id, derslik_id FROM inserted;
    END
END;


CREATE PROCEDURE sp_SinavEkle
    @ders_id INT,
    @tarih DATE,
    @oturum_id INT
AS
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO Sinav (ders_id, tarih, oturum_id)
        VALUES (@ders_id, @tarih, @oturum_id);

        COMMIT;
    END TRY
    BEGIN CATCH
        ROLLBACK;
        PRINT 'Hata oluştu, işlem geri alındı';
    END CATCH
END;


CREATE PROCEDURE sp_GozetmenAta
    @sinav_id INT,
    @personel_id INT
AS
BEGIN
    IF EXISTS (
        SELECT 1
        FROM Gozetmen_Atama ga
        JOIN Sinav s1 ON ga.sinav_id = s1.sinav_id
        JOIN Sinav s2 ON s2.sinav_id = @sinav_id
        WHERE ga.personel_id = @personel_id
        AND s1.tarih = s2.tarih
        AND s1.oturum_id = s2.oturum_id
    )
    BEGIN
        PRINT 'Bu personel aynı saat başka sınavda görevli!';
        RETURN;
    END

    INSERT INTO Gozetmen_Atama (sinav_id, personel_id)
    VALUES (@sinav_id, @personel_id);
END;


CREATE PROCEDURE sp_SinavListele
AS
BEGIN
    SELECT 
        d.ders_adi,
        s.tarih,
        o.aciklama AS oturum,
        dl.ad AS derslik
    FROM Sinav s
    JOIN Ders d ON s.ders_id = d.ders_id
    JOIN Oturum o ON s.oturum_id = o.oturum_id
    JOIN Sinav_Salon ss ON s.sinav_id = ss.sinav_id
    JOIN Derslik dl ON ss.derslik_id = dl.derslik_id
END;


CREATE FUNCTION fn_GorevSayisi (@personel_id INT)
RETURNS INT
AS
BEGIN
    DECLARE @sayi INT;

    SELECT @sayi = COUNT(*)
    FROM Gozetmen_Atama
    WHERE personel_id = @personel_id;

    RETURN @sayi;
END;

#SELECT dbo.fn_GorevSayisi(1) AS GorevSayisi;


CREATE FUNCTION fn_MusaitMi (
    @personel_id INT,
    @tarih DATE
)
RETURNS BIT
AS
BEGIN
    DECLARE @sonuc BIT;

    IF EXISTS (
        SELECT 1
        FROM Personel_Durum
        WHERE personel_id = @personel_id
        AND tarih = @tarih
        AND uygun_mu = 0
    )
        SET @sonuc = 0;
    ELSE
        SET @sonuc = 1;

    RETURN @sonuc;
END;


CREATE FUNCTION fn_KapasiteYeterliMi (@sinav_id INT)
RETURNS BIT
AS
BEGIN
    DECLARE @toplam INT;
    DECLARE @gereken INT;
    DECLARE @sonuc BIT;

    SELECT @toplam = SUM(d.kapasite)
    FROM Sinav_Salon ss
    JOIN Derslik d ON ss.derslik_id = d.derslik_id
    WHERE ss.sinav_id = @sinav_id;

    SELECT @gereken = ogrenci_sayisi
    FROM Ders
    WHERE ders_id = (
        SELECT ders_id FROM Sinav WHERE sinav_id = @sinav_id
    );

    IF @toplam >= @gereken
        SET @sonuc = 1;
    ELSE
        SET @sonuc = 0;

    RETURN @sonuc;
END;


CREATE VIEW vw_SinavProgrami AS
SELECT 
    d.ders_adi,
    s.tarih,
    o.aciklama AS oturum,
    dl.ad AS derslik
FROM Sinav s
JOIN Ders d ON s.ders_id = d.ders_id
JOIN Oturum o ON s.oturum_id = o.oturum_id
JOIN Sinav_Salon ss ON s.sinav_id = ss.sinav_id
JOIN Derslik dl ON ss.derslik_id = dl.derslik_id;

#SELECT * FROM vw_SinavProgrami;


CREATE TABLE Log_Kayitlari (
    log_id INT PRIMARY KEY IDENTITY(1,1),
    sinav_id INT,
    eski_tarih DATE,
    yeni_tarih DATE,
    eski_oturum_id INT,
    yeni_oturum_id INT,
    degistiren NVARCHAR(100),
    degisim_tarihi DATETIME DEFAULT GETDATE()
);

CREATE TRIGGER trg_Sinav_Log
ON Sinav
AFTER UPDATE
AS
BEGIN
    INSERT INTO Log_Kayitlari (
        sinav_id,
        eski_tarih,
        yeni_tarih,
        eski_oturum_id,
        yeni_oturum_id,
        degistiren
    )
    SELECT 
        d.sinav_id,
        d.tarih,
        i.tarih,
        d.oturum_id,
        i.oturum_id,
        SYSTEM_USER
    FROM deleted d
    JOIN inserted i ON d.sinav_id = i.sinav_id
    WHERE 
        d.tarih <> i.tarih
        OR d.oturum_id <> i.oturum_id;
END;

UPDATE Sinav
SET tarih = '2026-06-01'
WHERE sinav_id = 1;
SELECT * FROM Log_Kayitlari;



CREATE INDEX idx_sinav_ders ON Sinav(ders_id);
CREATE INDEX idx_sinav_oturum ON Sinav(oturum_id);
CREATE INDEX idx_gozetmen_personel ON Gozetmen_Atama(personel_id);
CREATE INDEX idx_sinav_salon ON Sinav_Salon(derslik_id);


ALTER TABLE Sinav
ADD CONSTRAINT uq_ders UNIQUE (ders_id);

ALTER TABLE Gozetmen_Atama
ADD CONSTRAINT uq_atama UNIQUE (sinav_id, personel_id);



CREATE LOGIN App_Admin WITH PASSWORD = 'Gulsen123';
CREATE USER App_Admin FOR LOGIN App_Admin;

CREATE LOGIN App_Viewer WITH PASSWORD = 'Gulsen123';
CREATE USER App_Viewer FOR LOGIN App_Viewer;


-- Admin full
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO App_Admin;

-- Viewer sadece okuma
GRANT SELECT ON SCHEMA::dbo TO App_Viewer;


